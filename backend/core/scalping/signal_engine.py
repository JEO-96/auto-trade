from __future__ import annotations

from .config import ScalpingAlertConfig
from .price_levels import calculate_price_levels
from .types import CandidateSnapshot, SignalDecision


class SignalEngine:
    def __init__(self, config: ScalpingAlertConfig) -> None:
        self.config = config

    def evaluate(self, snapshot: CandidateSnapshot) -> SignalDecision:
        score = 0
        reasons: list[str] = []
        rejections: list[str] = []

        if snapshot.is_halted:
            rejections.append("halted")
        if snapshot.trading_value_5m < self.config.min_trading_value_5m:
            rejections.append("trading value too low")
        if snapshot.trading_value_ratio < self.config.min_trading_value_ratio:
            rejections.append("trading value ratio too low")
        if snapshot.volume_ratio < self.config.min_volume_ratio:
            rejections.append("volume ratio too low")
        if snapshot.execution_strength < self.config.min_execution_strength:
            rejections.append("execution strength too weak")
        if snapshot.spread_pct > self.config.max_spread_pct:
            rejections.append("spread too wide")
        if snapshot.orderbook_imbalance < self.config.min_orderbook_imbalance:
            rejections.append("bid depth too weak")
        if snapshot.vwap > 0:
            vwap_extension = ((snapshot.price - snapshot.vwap) / snapshot.vwap) * 100.0
            if vwap_extension > self.config.max_vwap_extension_pct:
                rejections.append("too extended from VWAP")

        if snapshot.trading_value_5m >= self.config.min_trading_value_5m:
            score += 18
            reasons.append("거래대금 급증")
        if snapshot.trading_value_ratio >= self.config.min_trading_value_ratio:
            score += 14
            reasons.append("거래대금 평소 대비 확대")
        if snapshot.volume_ratio >= self.config.min_volume_ratio:
            score += 14
            reasons.append("거래량 급증")
        if snapshot.execution_strength >= self.config.min_execution_strength:
            score += 16
            reasons.append("체결강도 우위")
        if snapshot.price >= snapshot.vwap > 0:
            score += 12
            reasons.append("VWAP 상회")
        if snapshot.price >= snapshot.pivot_high > 0:
            score += 14
            reasons.append("당일 고점 재돌파")
        if snapshot.orderbook_imbalance >= self.config.min_orderbook_imbalance:
            score += 8
            reasons.append("호가 잔량 양호")
        if snapshot.is_vi_caution:
            score -= 8
            reasons.append("VI 주의")

        levels, level_rejection = calculate_price_levels(snapshot, self.config)
        if level_rejection:
            rejections.append(level_rejection)

        grade = "A" if score >= 85 else "B" if score >= self.config.min_score else "C"
        should_alert = not rejections and score >= self.config.min_score and levels is not None

        return SignalDecision(
            symbol=snapshot.symbol,
            name=snapshot.name,
            should_alert=should_alert,
            score=score,
            grade=grade,
            reasons=reasons,
            rejections=rejections,
            levels=levels,
        )
