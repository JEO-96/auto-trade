import httpx
import logging
from settings import settings

logger = logging.getLogger(__name__)


async def send_telegram_message(
    message: str,
    user_id: int | None = None,
    chat_id: str | None = None,
    use_html: bool = False,
) -> bool:
    """
    텔레그램 봇으로 메시지 전송.
    - chat_id 직접 지정: 해당 chat_id로 전송
    - user_id 지정: DB에서 해당 유저의 telegram_chat_id 조회 후 전송
    - 둘 다 없으면: 관리자 chat_id(settings)로 폴백
    - use_html: True이면 parse_mode=HTML (메시지에 <b>, <pre> 등 사용 시)
    """
    token = settings.telegram_bot_token
    if not token:
        logger.warning("[Telegram] Bot token not configured")
        return False

    # chat_id 결정
    target_chat_id = chat_id

    if not target_chat_id and user_id:
        # DB에서 유저의 telegram_chat_id 조회
        try:
            import database
            from models import User
            db = database.SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.telegram_chat_id:
                    target_chat_id = user.telegram_chat_id
            finally:
                db.close()
        except Exception as e:
            logger.error("[Telegram] DB lookup failed for user %d: %s", user_id, e)

    if not target_chat_id:
        # 관리자 chat_id로 폴백
        target_chat_id = settings.telegram_chat_id

    if not target_chat_id:
        logger.warning("[Telegram] No chat_id available (user_id=%s)", user_id)
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload: dict = {
        "chat_id": target_chat_id,
        "text": message,
    }
    if use_html:
        payload["parse_mode"] = "HTML"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)

            if response.status_code == 200:
                logger.info("[Telegram] Message sent to chat_id=%s", target_chat_id)
                return True
            else:
                logger.warning("[Telegram] Send failed: status %d, %s",
                             response.status_code, response.text)
                return False

    except Exception as e:
        logger.error("[Telegram] Error sending message: %s", e)
        return False


def _check_user_notification_setting(user_id: int, setting_name: str) -> bool:
    """유저의 알림 설정을 확인. 설정이 없거나 조회 실패 시 True(전송) 반환."""
    try:
        import database
        from models import User
        with database.get_db_session() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return True
            return getattr(user, setting_name, True)
    except Exception as e:
        logger.error("[Telegram] Failed to check notification setting for user %d: %s", user_id, e)
        return True  # 조회 실패 시 기본적으로 전송


async def send_trade_notification(user_id: int, message: str) -> bool:
    """매매 체결 알림 — 유저의 notification_trade 설정 확인 후 전송."""
    if not _check_user_notification_setting(user_id, "notification_trade"):
        logger.debug("[Telegram] Trade notification disabled for user %d", user_id)
        return False
    return await send_telegram_message(message, user_id=user_id)


async def send_bot_status_notification(user_id: int, message: str) -> bool:
    """봇 상태 변경 알림 — 유저의 notification_bot_status 설정 확인 후 전송."""
    if not _check_user_notification_setting(user_id, "notification_bot_status"):
        logger.debug("[Telegram] Bot status notification disabled for user %d", user_id)
        return False
    return await send_telegram_message(message, user_id=user_id)


async def send_system_notification(message: str) -> bool:
    """시스템 알림 — 관리자 chat_id로 전송 (사용자 설정과 무관하게 항상 전송)."""
    return await send_telegram_message(message)
