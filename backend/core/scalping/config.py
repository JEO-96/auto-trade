from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScalpingAlertConfig:
    max_daily_alerts: int = 10
    min_score: int = 78
    min_trading_value_5m: float = 3_000_000_000.0
    min_trading_value_ratio: float = 3.0
    min_volume_ratio: float = 2.5
    min_execution_strength: float = 115.0
    max_spread_pct: float = 0.35
    min_orderbook_imbalance: float = 0.48
    max_stop_pct: float = 3.0
    min_stop_pct: float = 0.6
    max_vwap_extension_pct: float = 5.0
    cooldown_minutes: int = 45
    ranking_limit: int = 50
    ranking_refresh_seconds: int = 30
    scan_tick_seconds: int = 2
    dry_run: bool = True
