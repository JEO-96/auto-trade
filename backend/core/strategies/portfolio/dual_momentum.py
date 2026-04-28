"""Dual Momentum (Antonacci) — ETF 단일자산 회전 전략.

평가 모드:
  - "sequential" (기본, v1 호환):
      방어자산 → 위험자산 순차 평가, 첫 번째로 채권을 이기는 위험자산 선택.
      069500이 채권 이기면 360750은 안 봄. v1 백테스트와 일치.
  - "best_momentum" (Antonacci 원작 정합):
      위험자산 중 lookback 수익률이 가장 큰 것을 골라 채권과 비교.
      이기면 그것, 아니면 채권.

데이터 부족인 위험자산은 후보에서 제외만 하고,
다른 위험자산 평가는 그대로 진행한다 (한 자산 부재가 전체 폴백을 유발하지 않음).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class DualMomentumStrategy:
    # 클래스 디폴트 (v1 호환). 인스턴스에서 오버라이드 가능.
    RISK_ASSETS: List[str] = ["069500", "360750"]
    DEFENSIVE_ASSET: str = "153130"
    LOOKBACK_MONTHS: int = 12
    EVALUATION_MODE: str = "sequential"

    def __init__(
        self,
        risk_assets: Optional[List[str]] = None,
        defensive_asset: Optional[str] = None,
        lookback_months: Optional[int] = None,
        evaluation_mode: Optional[str] = None,
    ) -> None:
        self.risk_assets: List[str] = list(risk_assets) if risk_assets is not None else list(self.RISK_ASSETS)
        self.defensive_asset: str = defensive_asset if defensive_asset is not None else self.DEFENSIVE_ASSET
        self.lookback_months: int = int(lookback_months) if lookback_months is not None else self.LOOKBACK_MONTHS
        mode = evaluation_mode if evaluation_mode is not None else self.EVALUATION_MODE
        if mode not in ("sequential", "best_momentum"):
            raise ValueError(f"Unknown evaluation_mode: {mode!r}")
        self.evaluation_mode: str = mode

    @property
    def ASSETS(self) -> List[str]:
        """모든 자산 (위험 + 방어). 중복 제거, 순서 보존."""
        seen: set = set()
        out: List[str] = []
        for a in [*self.risk_assets, self.defensive_asset]:
            if a not in seen:
                out.append(a)
                seen.add(a)
        return out

    def compute_weights(
        self,
        df_dict: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> Dict[str, float]:
        """date 기준으로 자산 비중 계산.

        df_dict: {asset_code: df}, 각 df는 columns=[timestamp, open, high, low, close, volume].
        """
        date = pd.Timestamp(date).normalize()
        lookback_date = date - pd.DateOffset(months=self.lookback_months)

        defensive_ret = self._compute_return(df_dict.get(self.defensive_asset), date, lookback_date)
        if defensive_ret is None:
            logger.debug(
                "DualMomentum: 방어자산 %s 데이터 부족 → 100%% 폴백 (date=%s)",
                self.defensive_asset, date,
            )
            return self._defensive_weights()

        # 위험자산 수익률 사전 수집 (데이터 부족이면 None)
        risk_returns: Dict[str, float] = {}
        for ra in self.risk_assets:
            r = self._compute_return(df_dict.get(ra), date, lookback_date)
            if r is None:
                logger.debug(
                    "DualMomentum: 위험자산 %s 데이터 부족 → 후보 제외 (date=%s)", ra, date,
                )
                continue
            risk_returns[ra] = r

        if self.evaluation_mode == "sequential":
            # v1 호환: 정의된 순서대로 평가, 채권 이기는 첫 자산 선택
            for ra in self.risk_assets:
                if ra not in risk_returns:
                    continue
                if risk_returns[ra] > defensive_ret:
                    return self._one_hot(ra)
            return self._defensive_weights()

        # best_momentum (Antonacci 원작): 모멘텀 max인 위험자산이 채권 이기면 그것
        if not risk_returns:
            return self._defensive_weights()
        best_asset = max(risk_returns, key=risk_returns.get)
        if risk_returns[best_asset] > defensive_ret:
            return self._one_hot(best_asset)
        return self._defensive_weights()

    # ─────────────────────────────────────────────────────
    # Internals
    # ─────────────────────────────────────────────────────

    @staticmethod
    def _compute_return(
        df: Optional[pd.DataFrame],
        date: pd.Timestamp,
        lookback_date: pd.Timestamp,
    ) -> Optional[float]:
        """date 기준 lookback 수익률. date / lookback_date 둘 다 가장 가까운 이전 거래일 종가 사용."""
        if df is None or df.empty:
            return None

        ts = pd.to_datetime(df["timestamp"]).dt.normalize()
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

    def _one_hot(self, asset: str) -> Dict[str, float]:
        return {a: (1.0 if a == asset else 0.0) for a in self.ASSETS}

    def _defensive_weights(self) -> Dict[str, float]:
        return self._one_hot(self.defensive_asset)
