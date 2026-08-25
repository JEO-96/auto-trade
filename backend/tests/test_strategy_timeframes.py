"""전략 전용 캔들 주기 정규화 테스트."""
import models
import schemas
from constants import resolve_strategy_timeframe
from routers import backtest, bots


def test_trend_rider_v1_uses_four_hour_candles() -> None:
    assert resolve_strategy_timeframe("trend_rider_4h_v1", "1h") == "4h"
    assert resolve_strategy_timeframe("trend_rider_4h_v1", "4h") == "4h"


def test_legacy_trend_rider_alias_uses_four_hour_candles() -> None:
    assert resolve_strategy_timeframe("steady_compounder", "1h") == "4h"


def test_invalid_strategy_timeframe_suffix_is_not_enforced() -> None:
    assert resolve_strategy_timeframe("unknown_999h", "1h") == "1h"


def test_missing_strategy_name_preserves_requested_timeframe() -> None:
    assert resolve_strategy_timeframe(None, "1h") == "1h"


def test_create_bot_normalizes_trend_rider_v1_timeframe(sample_user, db_session) -> None:
    bot = bots.create_bot(
        schemas.BotConfigCreate(
            symbol="BTC/KRW",
            strategy_name="trend_rider_4h_v1",
            timeframe="1h",
        ),
        sample_user,
        db_session,
    )

    assert bot.timeframe == "4h"


def test_update_bot_normalizes_existing_trend_rider_v1_timeframe(
    sample_user, db_session, monkeypatch
) -> None:
    bot = models.BotConfig(
        user_id=sample_user.id,
        symbol="BTC/KRW",
        strategy_name="trend_rider_4h_v1",
        timeframe="1h",
        paper_trading_mode=True,
        allocated_capital=1_000_000,
        is_active=False,
    )
    db_session.add(bot)
    db_session.commit()
    monkeypatch.setattr(bots, "_is_bot_running", lambda _bot_id: False)

    updated = bots.update_bot(
        bot.id,
        schemas.BotConfigUpdate(timeframe="1h"),
        sample_user,
        db_session,
    )

    assert updated.timeframe == "4h"


def test_backtest_normalizes_trend_rider_v1_timeframe(sample_user, db_session, monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakeVectorBacktester:
        def __init__(self, strategy_name: str):
            captured["strategy_name"] = strategy_name

        def start_async_backtest(self, **kwargs):
            captured["timeframe"] = kwargs["timeframe"]
            backtest.backtest_tasks["task-1"] = {}
            return "task-1"

    monkeypatch.setattr(backtest, "VectorBacktester", FakeVectorBacktester)

    response = backtest.run_backtest(
        schemas.BacktestRequest(
            symbol="BTC/KRW",
            strategy_name="trend_rider_4h_v1",
            timeframe="1h",
        ),
        sample_user,
        db_session,
    )

    assert response["status"] == "running"
    assert captured == {"strategy_name": "trend_rider_4h_v1", "timeframe": "4h"}
