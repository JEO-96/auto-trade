"""
에러 모니터링 모듈 — ERROR 이상 로그를 텔레그램으로 관리자에게 전송.
동일 에러 반복 전송 방지를 위해 60초 rate limit 적용.
"""

import asyncio
import logging
import threading
import time
import traceback


# 에러별 마지막 전송 시각 (key: 에러 식별자, value: timestamp)
_last_sent: dict[str, float] = {}
_lock = threading.Lock()

# 동일 에러 재전송 최소 간격 (초)
RATE_LIMIT_SECONDS = 60

# 텔레그램 메시지 내 traceback 최대 길이
MAX_TRACEBACK_LENGTH = 500


def _make_error_key(record: logging.LogRecord) -> str:
    """로그 레코드에서 에러 고유 식별자 생성 (모듈 + 메시지 앞 100자)."""
    msg_prefix = str(record.getMessage())[:100]
    return f"{record.name}:{msg_prefix}"


def _is_rate_limited(error_key: str) -> bool:
    """동일 에러가 최근 RATE_LIMIT_SECONDS 이내에 전송되었는지 확인."""
    now = time.time()
    with _lock:
        last = _last_sent.get(error_key)
        if last and (now - last) < RATE_LIMIT_SECONDS:
            return True
        _last_sent[error_key] = now

        # 오래된 항목 정리 (메모리 누수 방지, 1000개 초과 시)
        if len(_last_sent) > 1000:
            cutoff = now - RATE_LIMIT_SECONDS * 2
            expired = [k for k, v in _last_sent.items() if v < cutoff]
            for k in expired:
                del _last_sent[k]

        return False


def _format_telegram_message(record: logging.LogRecord) -> str:
    """텔레그램 전송용 에러 메시지 포맷."""
    # traceback 추출
    tb_text = ""
    if record.exc_info and record.exc_info[2]:
        tb_lines = traceback.format_exception(*record.exc_info)
        tb_text = "".join(tb_lines)
        if len(tb_text) > MAX_TRACEBACK_LENGTH:
            tb_text = tb_text[-MAX_TRACEBACK_LENGTH:] + "\n... (truncated)"

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))

    parts = [
        f"🚨 <b>[{record.levelname}]</b> 서버 에러 발생",
        f"<b>시각:</b> {timestamp}",
        f"<b>모듈:</b> {record.name}",
        f"<b>메시지:</b> {record.getMessage()[:300]}",
    ]

    if tb_text:
        parts.append(f"<b>Traceback:</b>\n<pre>{tb_text}</pre>")

    return "\n".join(parts)


class TelegramErrorHandler(logging.Handler):
    """
    ERROR 이상 로그를 텔레그램 관리자 채팅으로 전송하는 핸들러.
    - rate limiting으로 동일 에러 스팸 방지
    - 비동기 전송이므로 메인 앱 성능에 영향 없음
    - 전송 실패 시 조용히 무시 (앱 동작에 영향 없음)
    """

    def __init__(self, level: int = logging.ERROR):
        super().__init__(level)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # notifications 모듈 자체 에러의 무한 루프 방지
            if record.name == "notifications" or record.name.startswith("httpx"):
                return

            error_key = _make_error_key(record)
            if _is_rate_limited(error_key):
                return

            message = _format_telegram_message(record)
            self._send_async(message)

        except Exception:
            # 핸들러 에러가 앱에 영향을 주지 않도록 조용히 무시
            pass

    def _send_async(self, message: str) -> None:
        """비동기 텔레그램 전송을 논블로킹으로 실행."""
        try:
            loop = asyncio.get_running_loop()
            # 이미 이벤트 루프가 실행 중이면 태스크로 스케줄링
            loop.create_task(self._send(message))
        except RuntimeError:
            # 이벤트 루프가 없으면 새로 생성하여 실행 (스레드 환경)
            threading.Thread(
                target=self._send_in_new_loop,
                args=(message,),
                daemon=True,
            ).start()

    def _send_in_new_loop(self, message: str) -> None:
        """별도 스레드에서 새 이벤트 루프로 전송."""
        try:
            asyncio.run(self._send(message))
        except Exception:
            pass

    @staticmethod
    async def _send(message: str) -> None:
        """실제 텔레그램 메시지 전송."""
        try:
            from notifications import send_telegram_message
            await send_telegram_message(message)
        except Exception:
            pass
