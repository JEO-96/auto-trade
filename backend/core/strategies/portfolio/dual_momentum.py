"""Dual Momentum (Antonacci 단순화) — ETF 단일자산 회전 전략.

룰 (순차 적용):
  1) 방어자산 153130의 12M 수익률 계산 불가 → 153130 100% (안전 폴백)
  2) 069500의 12M 수익률 계산 가능 AND 069500_return > 153130_return → 069500 100%
  3) 360750의 12M 수익률 계산 가능 AND 360750_return > 153130_return → 360750 100%
  4) 그 외 → 153130 100%

데이터 부족인 위험자산은 후보에서 제외만 하고,
다른 위험자산 평가는 그대로 진행한다 (한 자산 부재가 전체 폴백을 유발하지 않음).
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Dict

import pandas as pd

logger = logging.getLogger(__name__)


class DualMomentumStrategy:
    RISK_ASSETS = ["069500", "360750"]
    DEFENSIVE_ASSET = "153130"
    ASSETS = ["069500", "360750", "153130"]

    LOOKBACK_MONTHS = 12

    def compute_weights(
        self,
        df_dict: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> Dict[str, float]:
        """date 기준으로 자산 비중 계산.

        df_dict: {"069500": df, "360750": df, "153130": df}
                 각 df는 columns=[timestamp, open, high, low, close, volume]
                 timestamp는 datetime, 오름차순 정렬되어 있다고 가정.

        데이터 부족인 위험자산은 후보에서 제외만 하고, 다른 자산 평가는 진행한다.
        방어자산(153130) 자체의 lookback이 불가능하면 안전하게 153130 100%로 폴백.
        """
        date = pd.Timestamp(date).normalize()
        lookback_date = date - pd.DateOffset(months=self.LOOKBACK_MONTHS)

        defensive_ret = self._compute_return(df_dict.get(self.DEFENSIVE_ASSET), date, lookback_date)
        if defensive_ret is None:
            logger.debug(
                "DualMomentum: 방어자산 %s 데이터 부족 → 153130 100%% 폴백 (date=%s)",
                self.DEFENSIVE_ASSET, date,
            )
            return self._defensive_weights()

        # 위험자산 순차 평가 — 데이터 없으면 그 자산만 후보에서 제외
        for risk_asset in self.RISK_ASSETS:
            risk_ret = self._compute_return(df_dict.get(risk_asset), date, lookback_date)
            if risk_ret is None:
                logger.debug(
                    "DualMomentum: 위험자산 %s 데이터 부족 → 후보 제외 (date=%s)",
                    risk_asset, date,
                )
                continue
            if risk_ret > defensive_ret:
                return self._one_hot(risk_asset)

        return self._defensive_weights()

    # ─────────────────────────────────────────────────────
    # Internals
    # ─────────────────────────────────────────────────────

    @staticmethod
    def _compute_return(
        df: pd.DataFrame,
        date: pd.Timestamp,
        lookback_date: pd.Timestamp,
    ) -> float | None:
        """date 기준 lookback 수익률.

        date / lookback_date 각각 가장 가까운 이전 거래일의 종가 사용.
        둘 중 하나라도 못 찾으면 None.
        """
        if df is None or df.empty:
            return None

        ts = pd.to_datetime(df["timestamp"]).dt.normalize()
        # 이전 거래일 종가
        recent_mask = ts <= date
        old_mask = ts <= lookback_date
        if not recent_mask.any() or not old_mask.any():
            return None

        recent_idx = ts[recent_mask].index[-1]
        old_idx = ts[old_mask].index[-1]

        recent_close = float(df.loc[recent_idx, "close"])
        old_close = float(df.loc[old_idx, "close"])
        if old_close == 0:
            return None
        return (recent_close - old_close) / old_close

    @classmethod
    def _one_hot(cls, asset: str) -> Dict[str, float]:
        return {a: (1.0 if a == asset else 0.0) for a in cls.ASSETS}

    @classmethod
    def _defensive_weights(cls) -> Dict[str, float]:
        return cls._one_hot(cls.DEFENSIVE_ASSET)
