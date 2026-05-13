import pytest

import schemas
from notifications import send_stock_alert_broadcast, send_stock_alert_notification
from routers.auth import get_me, get_notification_settings, update_notification_settings


def test_notification_settings_include_stock_alert_toggle(db_session, sample_user):
    assert get_notification_settings(sample_user).notification_stock_alert is False

    updated = update_notification_settings(
        schemas.NotificationSettings(
            notification_trade=True,
            notification_bot_status=True,
            notification_system=True,
            notification_stock_alert=True,
            notification_interval="4h",
        ),
        current_user=sample_user,
        db=db_session,
    )

    assert updated.notification_stock_alert is True
    assert sample_user.notification_stock_alert is True
    assert get_me(sample_user, db_session).notification_stock_alert is True


@pytest.mark.anyio
async def test_stock_alert_notification_respects_user_toggle(monkeypatch, mock_get_db_session, sample_user):
    mock_get_db_session_fn, db_session = mock_get_db_session
    sample_user.telegram_chat_id = "12345"
    sample_user.notification_stock_alert = False
    db_session.commit()

    import database
    import notifications

    sent: list[tuple[str, int | None]] = []

    async def fake_send(message: str, user_id: int | None = None, **kwargs):
        sent.append((message, user_id))
        return True

    monkeypatch.setattr(database, "get_db_session", mock_get_db_session_fn)
    monkeypatch.setattr(notifications, "send_telegram_message", fake_send)

    disabled = await send_stock_alert_notification(sample_user.id, "stock alert")
    assert disabled is False
    assert sent == []

    sample_user.notification_stock_alert = True
    db_session.commit()

    enabled = await send_stock_alert_notification(sample_user.id, "stock alert")
    assert enabled is True
    assert sent == [("stock alert", sample_user.id)]


@pytest.mark.anyio
async def test_stock_alert_broadcast_sends_only_opted_in_telegram_users(
    monkeypatch,
    mock_get_db_session,
    sample_user,
    db_session,
):
    mock_get_db_session_fn, _ = mock_get_db_session
    sample_user.telegram_chat_id = "12345"
    sample_user.notification_stock_alert = True

    opted_out = __import__("models").User(
        id=2,
        email="disabled@example.com",
        nickname="disabled",
        is_active=True,
        telegram_chat_id="67890",
        notification_stock_alert=False,
    )
    no_chat = __import__("models").User(
        id=3,
        email="no-chat@example.com",
        nickname="no-chat",
        is_active=True,
        telegram_chat_id=None,
        notification_stock_alert=True,
    )
    db_session.add_all([opted_out, no_chat])
    db_session.commit()

    import database
    import notifications

    sent: list[int | None] = []

    async def fake_send(message: str, user_id: int | None = None, **kwargs):
        sent.append(user_id)
        return True

    monkeypatch.setattr(database, "get_db_session", mock_get_db_session_fn)
    monkeypatch.setattr(notifications, "send_telegram_message", fake_send)

    result = await send_stock_alert_broadcast("stock alert")

    assert result == {"sent": 1, "failed": 0, "eligible": 1}
    assert sent == [sample_user.id]
