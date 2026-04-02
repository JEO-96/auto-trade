"""
OKX 선물 멀티심볼 자동매매 봇 — Ultimate Ensemble Strategy

사용법:
    cd backend
    python -m okx_futures.bot

환경변수 (.env):
    OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from okx_futures.exchange import (
    create_okx_client,
    fetch_ohlcv,
    get_balance,
    get_position,
    set_leverage,
    place_market_order,
    place_sl_tp_orders,
    cancel_all_orders,
)
from okx_futures.strategy import SmartTrendFuturesStrategy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("okx_futures_bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("okx_futures")

# 설정
SYMBOLS = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
]
TIMEFRAME = "1h"
CHECK_INTERVAL_SEC = 60
LEVERAGE = 3
MAX_POSITIONS = 2


class OKXFuturesBot:
    """OKX 선물 멀티심볼 자동매매 봇"""

    def __init__(self):
        self.exchange = create_okx_client()
        # 심볼별 전략 인스턴스
        self.strategies: dict[str, SmartTrendFuturesStrategy] = {
            sym: SmartTrendFuturesStrategy() for sym in SYMBOLS
        }
        self.last_signal_times: dict[str, str] = {}
        self.running = False

    def initialize(self):
        """초기화"""
        logger.info("=" * 60)
        logger.info("OKX 선물 멀티심볼 봇 초기화")
        logger.info(f"심볼: {', '.join(s.split('/')[0] for s in SYMBOLS)}")
        logger.info(f"타임프레임: {TIMEFRAME} | 레버리지: {LEVERAGE}x | 최대 포지션: {MAX_POSITIONS}")
        logger.info("=" * 60)

        # 각 심볼 레버리지 설정
        for sym in SYMBOLS:
            set_leverage(self.exchange, sym, LEVERAGE)

        # 잔고
        balance = get_balance(self.exchange)
        logger.info(f"USDT 잔고 - Total: {balance['total']:.2f} | Free: {balance['free']:.2f}")

        if balance["free"] < 10:
            logger.warning("가용 잔고 10 USDT 미만")

        # 기존 포지션
        for sym in SYMBOLS:
            pos = get_position(self.exchange, sym)
            if pos:
                logger.info(f"  {sym}: {pos['side']} {pos['size']} @ {pos['entry_price']:.4f}")

        return balance

    async def run_loop(self):
        self.running = True
        logger.info("봇 루프 시작")

        while self.running:
            try:
                await self._tick()
            except KeyboardInterrupt:
                logger.info("사용자에 의해 봇 중지")
                self.running = False
                break
            except Exception as e:
                logger.error(f"틱 에러: {e}", exc_info=True)

            await asyncio.sleep(CHECK_INTERVAL_SEC)

    async def _tick(self):
        """단일 봇 사이클 — 모든 심볼 순회"""
        # 현재 열린 포지션 수 확인
        open_positions = []
        for sym in SYMBOLS:
            pos = get_position(self.exchange, sym)
            if pos:
                open_positions.append(sym)

        for sym in SYMBOLS:
            try:
                await self._tick_symbol(sym, len(open_positions), sym in open_positions)
            except Exception as e:
                logger.error(f"{sym} 처리 에러: {e}")

    async def _tick_symbol(self, symbol: str, open_count: int, has_position: bool):
        """심볼별 처리"""
        strategy = self.strategies[symbol]

        # OHLCV 조회
        df = fetch_ohlcv(self.exchange, symbol, TIMEFRAME, limit=300)
        if len(df) < 210:
            return

        # 지표 적용
        df = strategy.apply_indicators(df)
        current_idx = len(df) - 2

        # 중복 신호 방지
        candle_time = str(df.index[current_idx])
        if self.last_signal_times.get(symbol) == candle_time:
            return

        # 주기적 상태 로깅
        now = datetime.now(timezone.utc)
        if now.minute % 30 == 0 and now.second < 70:
            summary = strategy.get_signal_summary(df, current_idx)
            long_s, short_s = strategy.get_signal_score(df, current_idx)
            coin = symbol.split("/")[0]
            logger.info(
                f"{coin} | close={summary['close']:.4f} "
                f"L={long_s}/10 S={short_s}/10 "
                f"RSI={summary['rsi']:.1f} ADX={summary['adx']:.1f}"
            )

        # 포지션 있으면 스킵 (SL/TP는 거래소에서 자동 처리)
        if has_position:
            return

        # 최대 포지션 초과시 스킵
        if open_count >= MAX_POSITIONS:
            return

        # 시그널 체크
        signal = strategy.check_signal(df, current_idx)
        if signal is None:
            return

        self.last_signal_times[symbol] = candle_time
        await self._open_position(symbol, signal, df, current_idx)

    async def _open_position(self, symbol: str, signal: str, df, current_idx: int):
        """포지션 진입"""
        strategy = self.strategies[symbol]
        entry_price = df.iloc[current_idx]["close"]
        sl, tp = strategy.calculate_exit_levels(df, current_idx, entry_price, signal)

        balance = get_balance(self.exchange)
        free = balance["free"]

        # 포지션 크기 계산
        position_size = strategy.calculate_position_size(free, entry_price, sl)
        if position_size <= 0:
            logger.warning(f"{symbol} 포지션 크기 0 - 잔고 부족")
            return

        margin_required = (position_size * entry_price) / LEVERAGE
        if margin_required > free * 0.9:
            position_size = (free * 0.9 * LEVERAGE) / entry_price
            position_size = round(position_size, 4)

        # OKX 최소 주문 크기 체크
        min_amounts = {"BTC": 0.001, "ETH": 0.01, "LINK": 0.1, "AVAX": 0.1}
        coin = symbol.split("/")[0]
        min_amt = min_amounts.get(coin, 0.01)
        if position_size < min_amt:
            logger.warning(f"{symbol} 최소 주문 크기 미달: {position_size} < {min_amt}")
            return

        position_size = round(position_size, 4)

        long_s, short_s = strategy.get_signal_score(df, current_idx)
        score = long_s if signal == "long" else short_s

        logger.info("=" * 55)
        logger.info(
            f"{'LONG' if signal == 'long' else 'SHORT'} 진입 | {coin} "
            f"| score={score}/10 | {position_size}"
        )
        logger.info(f"  진입가: {entry_price:.4f}")
        logger.info(f"  SL: {sl:.4f} ({abs(sl - entry_price) / entry_price * 100:.2f}%)")
        logger.info(f"  TP: {tp:.4f} ({abs(tp - entry_price) / entry_price * 100:.2f}%)")
        logger.info(f"  증거금: {margin_required:.2f} USDT")
        logger.info("=" * 55)

        side = "buy" if signal == "long" else "sell"
        try:
            order = place_market_order(self.exchange, symbol, side, position_size)
            logger.info(f"주문 체결: {order.get('id', 'N/A')}")
            place_sl_tp_orders(self.exchange, symbol, signal, position_size, sl, tp)
        except Exception as e:
            logger.error(f"주문 실패: {e}", exc_info=True)

    def stop(self):
        self.running = False
        logger.info("봇 중지 요청됨")


async def main():
    bot = OKXFuturesBot()
    try:
        bot.initialize()
        await bot.run_loop()
    except KeyboardInterrupt:
        logger.info("프로그램 종료")
    finally:
        bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
