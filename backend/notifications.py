import httpx
import logging
from settings import settings

logger = logging.getLogger(__name__)


async def send_telegram_message(message: str) -> bool:
    """
    텔레그램 봇으로 메시지 전송.
    카카오와 달리 유저별 토큰 불필요 — 봇 토큰 + chat_id로 전송.
    """
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    if not token or not chat_id:
        logger.warning("[Telegram] Bot token or chat_id not configured")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)

            if response.status_code == 200:
                logger.info("[Telegram] Message sent successfully")
                return True
            else:
                logger.warning("[Telegram] Send failed: status %d, %s",
                             response.status_code, response.text)
                return False

    except Exception as e:
        logger.error("[Telegram] Error sending message: %s", e)
        return False
