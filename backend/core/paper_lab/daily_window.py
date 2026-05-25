from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def kst_daily_window(now: datetime) -> tuple[datetime, datetime]:
    """Return the KST 09:00-to-09:00 window that contains ``now``."""
    now_kst = now.astimezone(KST) if now.tzinfo else now.replace(tzinfo=KST)
    today_9am = now_kst.replace(hour=9, minute=0, second=0, microsecond=0)
    start = today_9am if now_kst >= today_9am else today_9am - timedelta(days=1)
    return start, start + timedelta(days=1)
