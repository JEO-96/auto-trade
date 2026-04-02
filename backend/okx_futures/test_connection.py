"""
OKX API 연결 테스트

사용법:
    cd backend
    python -m okx_futures.test_connection
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from okx_futures.exchange import create_okx_client, fetch_ohlcv, get_balance, get_position
from okx_futures.strategy import SmartTrendFuturesStrategy


def test():
    print("=" * 60)
    print("OKX 선물 API 연결 테스트")
    print("=" * 60)

    # 1. 클라이언트 생성
    print("\n[1] OKX 클라이언트 생성...")
    try:
        exchange = create_okx_client()
        print("    ✅ 클라이언트 생성 성공")
    except Exception as e:
        print(f"    ❌ 실패: {e}")
        return

    # 2. 잔고 조회
    print("\n[2] USDT 잔고 조회...")
    try:
        balance = get_balance(exchange)
        print(f"    ✅ Total: {balance['total']:.2f} USDT")
        print(f"    ✅ Free:  {balance['free']:.2f} USDT")
        print(f"    ✅ Used:  {balance['used']:.2f} USDT")
    except Exception as e:
        print(f"    ❌ 실패: {e}")

    # 3. OHLCV 데이터 조회
    print("\n[3] BTC/USDT:USDT 1h OHLCV 조회...")
    try:
        df = fetch_ohlcv(exchange, "BTC/USDT:USDT", "1h", limit=100)
        print(f"    ✅ {len(df)}개 봉 조회 완료")
        print(f"    최신 봉: {df.index[-1]}")
        print(f"    현재가:  {df.iloc[-1]['close']:.2f} USDT")
    except Exception as e:
        print(f"    ❌ 실패: {e}")
        return

    # 4. 전략 지표 적용 테스트
    print("\n[4] 전략 지표 적용 테스트...")
    try:
        strategy = SmartTrendFuturesStrategy()
        df = fetch_ohlcv(exchange, "BTC/USDT:USDT", "1h", limit=300)
        df = strategy.apply_indicators(df)
        summary = strategy.get_signal_summary(df, len(df) - 2)
        print(f"    ✅ 지표 적용 완료")
        print(f"    추세: {summary['trend']}")
        print(f"    RSI:  {summary['rsi']:.1f}")
        print(f"    ADX:  {summary['adx']:.1f}")
        print(f"    MACD hist: {summary['macd_hist']:.4f}")
        print(f"    Vol ratio: {summary['vol_ratio']:.2f}x")

        # 시그널 체크
        signal = strategy.check_signal(df, len(df) - 2)
        if signal:
            print(f"    🔔 현재 시그널: {signal.upper()}")
        else:
            print(f"    ⏸️ 현재 시그널 없음 (대기 중)")
    except Exception as e:
        print(f"    ❌ 실패: {e}")

    # 5. 포지션 조회
    print("\n[5] 현재 포지션 조회...")
    try:
        pos = get_position(exchange, "BTC/USDT:USDT")
        if pos:
            print(f"    ✅ {pos['side']} {pos['size']} @ {pos['entry_price']:.2f}")
            print(f"    PnL: {pos['unrealized_pnl']:.2f} USDT")
        else:
            print("    ✅ 열린 포지션 없음")
    except Exception as e:
        print(f"    ❌ 실패: {e}")

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    test()
