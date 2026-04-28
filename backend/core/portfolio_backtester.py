"""포트폴리오 백테스터 — 월말 리밸런싱, 단일자산 100% 회전 (v1).

직접 구현 (vectorbt 미사용) — 디버깅 가능성과 명확성 우선.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from core.portfolio_strategy_registry import get_portfolio_strategy
from core.stock_data_fetcher import StockDataFetcher

logger = logging.getLogger(__name__)


class PortfolioBacktester:
    # 리밸런스 주기 → pandas freq alias 매핑
    _REBALANCE_FREQ_MAP: Dict[str, List[str]] = {
        "monthly": ["ME", "M"],   # 월말
        "quarterly": ["QE", "Q"],  # 분기말
        "semiannual": ["2QE", "2Q"],  # 반기말
    }

    def __init__(
        self,
        strategy_name: str = "dual_momentum_etf_v1",
        commission_rate: float = 0.001,
        lookback_months: Optional[int] = None,
        evaluation_mode: Optional[str] = None,
        rebalance_freq: str = "monthly",
    ) -> None:
        self.strategy_name = strategy_name
        self.commission_rate = float(commission_rate)
        self.strategy = get_portfolio_strategy(
            strategy_name,
            lookback_months=lookback_months,
            evaluation_mode=evaluation_mode,
        )
        if rebalance_freq not in self._REBALANCE_FREQ_MAP:
            raise ValueError(
                f"Unknown rebalance_freq: {rebalance_freq!r}. "
                f"Available: {list(self._REBALANCE_FREQ_MAP.keys())}"
            )
        self.rebalance_freq = rebalance_freq
        self.fetcher = StockDataFetcher()

    # ─────────────────────────────────────────────────────
    # Entry point
    # ─────────────────────────────────────────────────────

    def run(
        self,
        start_date: str,
        end_date: str,
        initial_capital: float,
        db: Optional[Session] = None,
    ) -> dict:
        assets: List[str] = list(self.strategy.ASSETS)
        # lookback_months에 비례하는 버퍼 (1.1배 + 60일 여유)
        lookback_buffer_days = int(self.strategy.lookback_months * 30.5 * 1.1) + 60

        start_dt = pd.Timestamp(start_date).normalize()
        end_dt = pd.Timestamp(end_date).normalize()
        if end_dt < start_dt:
            raise ValueError("end_date must be >= start_date")

        fetch_start = (start_dt - pd.Timedelta(days=lookback_buffer_days)).strftime("%Y-%m-%d")
        fetch_end = end_dt.strftime("%Y-%m-%d")

        df_dict: Dict[str, pd.DataFrame] = {}
        for asset in assets:
            df = self.fetcher.fetch_ohlcv(asset, fetch_start, fetch_end, db=db)
            if df.empty:
                logger.warning("PortfolioBacktester: %s 데이터 없음", asset)
            df_dict[asset] = df

        rebalance_dates = self._rebalance_dates(start_dt, end_dt)
        if not rebalance_dates:
            return self._empty_result(initial_capital, assets)

        # 백테스트 시뮬레이션
        cash = float(initial_capital)
        # 보유 자산 — 단일자산 회전이므로 최대 1개
        held_asset: Optional[str] = None
        held_units: float = 0.0

        equity_curve: List[Dict[str, Any]] = []
        rebalance_log: List[Dict[str, Any]] = []
        trades: List[Dict[str, Any]] = []
        holding_periods: Dict[str, int] = {a: 0 for a in assets}

        prev_rebalance_date: Optional[pd.Timestamp] = None
        prev_selected_asset: Optional[str] = None

        for rb_date in rebalance_dates:
            weights = self.strategy.compute_weights(df_dict, rb_date)
            selected_asset = self._select_asset_from_weights(weights)

            # 직전 보유 자산의 보유 일수 누적
            if prev_rebalance_date is not None and prev_selected_asset is not None:
                days_held = (rb_date - prev_rebalance_date).days
                holding_periods[prev_selected_asset] = holding_periods.get(prev_selected_asset, 0) + days_held

            # 리밸런싱 시점 가격 (이 날짜에 사용 가능한 가장 가까운 이전 거래일 종가)
            prices_at_rb = {a: self._price_at_or_before(df_dict.get(a), rb_date) for a in assets}

            # 현재 보유 자산 평가 → 매도 (자산 변경 시)
            if held_asset is not None and held_asset != selected_asset:
                sell_price = prices_at_rb.get(held_asset)
                if sell_price is None or math.isnan(sell_price):
                    logger.warning(
                        "PortfolioBacktester: %s 매도 가격 없음 @ %s — 매도 skip",
                        held_asset, rb_date.date(),
                    )
                else:
                    proceeds = held_units * sell_price
                    fee = proceeds * self.commission_rate
                    cash += proceeds - fee
                    trades.append({
                        "date": rb_date.strftime("%Y-%m-%d"),
                        "side": "SELL",
                        "asset": held_asset,
                        "price": float(sell_price),
                        "units": float(held_units),
                        "proceeds": float(proceeds),
                        "fee": float(fee),
                    })
                    held_asset = None
                    held_units = 0.0

            # 새 자산 매수 (보유 없을 때 + selected가 결정됐을 때)
            if held_asset is None and selected_asset is not None:
                buy_price = prices_at_rb.get(selected_asset)
                if buy_price is None or math.isnan(buy_price) or buy_price <= 0:
                    logger.warning(
                        "PortfolioBacktester: %s 매수 가격 없음 @ %s — 현금 보유",
                        selected_asset, rb_date.date(),
                    )
                else:
                    # commission 차감 후 매수 가능 금액
                    invest_amount = cash / (1.0 + self.commission_rate)
                    units = invest_amount / buy_price
                    fee = invest_amount * self.commission_rate
                    cash -= (invest_amount + fee)
                    held_asset = selected_asset
                    held_units = units
                    trades.append({
                        "date": rb_date.strftime("%Y-%m-%d"),
                        "side": "BUY",
                        "asset": selected_asset,
                        "price": float(buy_price),
                        "units": float(units),
                        "cost": float(invest_amount),
                        "fee": float(fee),
                    })

            # 포트폴리오 평가 (이 시점)
            held_value = (held_units * prices_at_rb[held_asset]) if held_asset and prices_at_rb.get(held_asset) else 0.0
            portfolio_value = cash + held_value
            equity_curve.append({
                "time": rb_date.strftime("%Y-%m-%d"),
                "value": float(round(portfolio_value, 4)),
            })
            rebalance_log.append({
                "date": rb_date.strftime("%Y-%m-%d"),
                "selected_asset": selected_asset,
                "weights": weights,
                "portfolio_value": float(round(portfolio_value, 4)),
            })

            prev_rebalance_date = rb_date
            prev_selected_asset = selected_asset

        # 마지막 자산 보유 일수 누적 (마지막 리밸런싱 → end_dt)
        if prev_rebalance_date is not None and prev_selected_asset is not None:
            days_held = max((end_dt - prev_rebalance_date).days, 0)
            holding_periods[prev_selected_asset] = holding_periods.get(prev_selected_asset, 0) + days_held

        # 최종 평가 (end_dt 기준 종가)
        final_prices = {a: self._price_at_or_before(df_dict.get(a), end_dt) for a in assets}
        held_value = (held_units * final_prices[held_asset]) if held_asset and final_prices.get(held_asset) else 0.0
        final_capital = cash + held_value

        # equity curve 마지막 포인트 갱신 (end_dt 기준).
        # 마지막 리밸런싱 날짜와 end_dt가 같으면 덮어쓴다 (차트 중복 점 방지).
        end_point = {
            "time": end_dt.strftime("%Y-%m-%d"),
            "value": float(round(final_capital, 4)),
        }
        if equity_curve and equity_curve[-1]["time"] == end_point["time"]:
            equity_curve[-1] = end_point
        else:
            equity_curve.append(end_point)

        metrics = self._compute_metrics(
            initial_capital, final_capital, equity_curve, start_dt, end_dt, self.rebalance_freq,
        )

        # Buy-and-hold 벤치마크 — 각 자산을 시작일에 매수해 끝까지 보유했다면?
        # 리밸런스 시점들(equity_curve와 동일 시간축)에서의 자산 평가액 곡선.
        rebalance_times = [pd.Timestamp(p["time"]) for p in equity_curve]
        benchmarks = self._compute_buy_and_hold(
            assets, df_dict, rebalance_times, initial_capital, self.commission_rate,
        )

        return {
            "strategy_name": self.strategy_name,
            "assets": assets,
            "initial_capital": float(initial_capital),
            "final_capital": float(round(final_capital, 4)),
            "total_return": metrics["total_return"],
            "cagr": metrics["cagr"],
            "max_drawdown": metrics["max_drawdown"],
            "sharpe": metrics["sharpe"],
            "total_rebalances": len(rebalance_log),
            "holding_periods": holding_periods,  # 자산별 보유 일수
            "equity_curve": equity_curve,
            "trades": trades,
            "rebalance_log": rebalance_log,
            "benchmarks": benchmarks,  # {asset: [{time, value}]} BH 곡선
        }

    def _compute_buy_and_hold(
        self,
        assets: List[str],
        df_dict: Dict[str, pd.DataFrame],
        timeline: List[pd.Timestamp],
        initial_capital: float,
        commission_rate: float,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """각 자산을 timeline[0]에 시장가 매수 후 보유한 가치 곡선.

        매수 비용 = invest * (1 + commission), units = invest / first_price.
        끝점에서는 매도 수수료까지 차감해 표시.
        """
        out: Dict[str, List[Dict[str, Any]]] = {}
        if not timeline:
            return out
        start = timeline[0]
        end = timeline[-1]

        for asset in assets:
            df = df_dict.get(asset)
            buy_px = self._price_at_or_before(df, start)
            if buy_px is None or buy_px <= 0:
                continue
            invest = initial_capital / (1.0 + commission_rate)
            units = invest / buy_px
            curve: List[Dict[str, Any]] = []
            for t in timeline:
                px = self._price_at_or_before(df, t)
                if px is None:
                    continue
                value = units * px
                if t == end:
                    # 종가에서 한 번 매도 가정 → 수수료 차감
                    value *= (1.0 - commission_rate)
                curve.append({"time": t.strftime("%Y-%m-%d"), "value": float(round(value, 4))})
            if curve:
                out[asset] = curve
        return out

    # ─────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────

    def _rebalance_dates(self, start_dt: pd.Timestamp, end_dt: pd.Timestamp) -> List[pd.Timestamp]:
        """rebalance_freq에 따른 리밸런스 일자 리스트.

        pandas ≥2.2에서는 'ME'/'QE' alias를 쓰고, 1.x에서는 'M'/'Q'로 fallback.
        반기('2Q')는 분기 인덱스에서 짝수 분기만 추출.
        """
        if self.rebalance_freq == "semiannual":
            for q_alias in self._REBALANCE_FREQ_MAP["quarterly"]:
                try:
                    idx = pd.date_range(start=start_dt, end=end_dt, freq=q_alias)
                    break
                except (ValueError, KeyError):
                    idx = None
            if idx is None or len(idx) == 0:
                return []
            # 분기 중 6/12월말만 (반기)
            return [pd.Timestamp(d).normalize() for d in idx if d.month in (6, 12)]

        for alias in self._REBALANCE_FREQ_MAP[self.rebalance_freq]:
            try:
                idx = pd.date_range(start=start_dt, end=end_dt, freq=alias)
                return [pd.Timestamp(d).normalize() for d in idx]
            except (ValueError, KeyError):
                continue
        return []

    @staticmethod
    def _price_at_or_before(df: Optional[pd.DataFrame], date: pd.Timestamp) -> Optional[float]:
        if df is None or df.empty:
            return None
        ts = pd.to_datetime(df["timestamp"]).dt.normalize()
        mask = ts <= pd.Timestamp(date).normalize()
        if not mask.any():
            return None
        idx = ts[mask].index[-1]
        return float(df.loc[idx, "close"])

    @staticmethod
    def _select_asset_from_weights(weights: Dict[str, float]) -> Optional[str]:
        """단일자산 회전 — weight 1.0인 자산 반환. 모두 0이면 None."""
        if not weights:
            return None
        for a, w in weights.items():
            if w >= 0.999:
                return a
        # weight 합이 0인 케이스 (이론상 안 옴) → None
        return None

    @staticmethod
    def _compute_metrics(
        initial_capital: float,
        final_capital: float,
        equity_curve: List[Dict[str, Any]],
        start_dt: pd.Timestamp,
        end_dt: pd.Timestamp,
        rebalance_freq: str = "monthly",
    ) -> dict:
        total_return = (final_capital - initial_capital) / initial_capital if initial_capital else 0.0

        years = max((end_dt - start_dt).days / 365.25, 1e-9)
        if final_capital > 0 and initial_capital > 0:
            cagr = (final_capital / initial_capital) ** (1 / years) - 1
        else:
            cagr = 0.0

        # MDD + Sharpe (월간 수익률 기준)
        values = np.array([p["value"] for p in equity_curve], dtype=float)
        if len(values) >= 2:
            running_max = np.maximum.accumulate(values)
            drawdowns = (values - running_max) / running_max
            mdd = float(drawdowns.min())

            rets = np.diff(values) / values[:-1]
            rets = rets[np.isfinite(rets)]
            if len(rets) > 1 and rets.std(ddof=0) > 0:
                # 리밸런스 주기별 연간 횟수 → Sharpe 연환산
                periods_per_year = {"monthly": 12, "quarterly": 4, "semiannual": 2}.get(rebalance_freq, 12)
                sharpe = float((rets.mean() / rets.std(ddof=0)) * math.sqrt(periods_per_year))
            else:
                sharpe = 0.0
        else:
            mdd = 0.0
            sharpe = 0.0

        return {
            "total_return": float(round(total_return, 6)),
            "cagr": float(round(cagr, 6)),
            "max_drawdown": float(round(mdd, 6)),
            "sharpe": float(round(sharpe, 6)),
        }

    @staticmethod
    def _empty_result(initial_capital: float, assets: List[str]) -> dict:
        return {
            "strategy_name": "dual_momentum_etf_v1",
            "assets": assets,
            "initial_capital": float(initial_capital),
            "final_capital": float(initial_capital),
            "total_return": 0.0,
            "cagr": 0.0,
            "max_drawdown": 0.0,
            "sharpe": 0.0,
            "total_rebalances": 0,
            "holding_periods": {a: 0 for a in assets},
            "equity_curve": [],
            "trades": [],
            "rebalance_log": [],
        }
