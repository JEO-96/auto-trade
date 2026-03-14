import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure root logger for the entire backend application.
    Call once at startup (in main.py) before any other imports that use logging.
    """
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)

    # Avoid duplicate handlers if called more than once
    if not root.handlers:
        root.addHandler(handler)

    # Silence overly verbose third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def setup_error_monitoring() -> None:
    """
    텔레그램 에러 모니터링 핸들러를 루트 로거에 등록.
    main.py 서버 시작 시 호출. 텔레그램 설정이 없으면 건너뜀.
    """
    from settings import settings

    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logging.getLogger(__name__).warning(
            "[ErrorMonitor] Telegram not configured — error monitoring disabled"
        )
        return

    from error_monitor import TelegramErrorHandler

    root = logging.getLogger()

    # 중복 등록 방지
    for h in root.handlers:
        if isinstance(h, TelegramErrorHandler):
            return

    handler = TelegramErrorHandler(level=logging.ERROR)
    root.addHandler(handler)

    logging.getLogger(__name__).info(
        "[ErrorMonitor] Telegram error monitoring enabled"
    )
