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
