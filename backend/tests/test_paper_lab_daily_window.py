from datetime import datetime, timedelta

import pytest
from zoneinfo import ZoneInfo

from core.paper_lab.daily_window import kst_daily_window

KST = ZoneInfo("Asia/Seoul")
UTC = ZoneInfo("UTC")


def test_after_9am_kst_starts_today():
    now = datetime(2026, 5, 25, 10, 0, tzinfo=KST)
    start, end = kst_daily_window(now)
    assert start == datetime(2026, 5, 25, 9, 0, tzinfo=KST)
    assert end == datetime(2026, 5, 26, 9, 0, tzinfo=KST)


def test_before_9am_kst_starts_yesterday():
    now = datetime(2026, 5, 25, 8, 0, tzinfo=KST)
    start, end = kst_daily_window(now)
    assert start == datetime(2026, 5, 24, 9, 0, tzinfo=KST)
    assert end == datetime(2026, 5, 25, 9, 0, tzinfo=KST)


def test_exactly_9am_kst_starts_today():
    now = datetime(2026, 5, 25, 9, 0, tzinfo=KST)
    start, end = kst_daily_window(now)
    assert start == datetime(2026, 5, 25, 9, 0, tzinfo=KST)
    assert end == datetime(2026, 5, 26, 9, 0, tzinfo=KST)


def test_utc_input_after_kst_9am():
    # 2026-05-25 01:00 UTC = 2026-05-25 10:00 KST
    now_utc = datetime(2026, 5, 25, 1, 0, tzinfo=UTC)
    start, end = kst_daily_window(now_utc)
    assert start == datetime(2026, 5, 25, 9, 0, tzinfo=KST)
    assert end == datetime(2026, 5, 26, 9, 0, tzinfo=KST)


def test_utc_input_before_kst_9am():
    # 2026-05-24 23:30 UTC = 2026-05-25 08:30 KST
    now_utc = datetime(2026, 5, 24, 23, 30, tzinfo=UTC)
    start, end = kst_daily_window(now_utc)
    assert start == datetime(2026, 5, 24, 9, 0, tzinfo=KST)
    assert end == datetime(2026, 5, 25, 9, 0, tzinfo=KST)


def test_window_duration_is_exactly_24h():
    now = datetime(2026, 5, 25, 12, 0, tzinfo=KST)
    start, end = kst_daily_window(now)
    assert end - start == timedelta(hours=24)


def test_start_always_has_hour_9_minute_0():
    for hour in [0, 5, 8, 9, 12, 23]:
        now = datetime(2026, 5, 25, hour, 30, tzinfo=KST)
        start, _ = kst_daily_window(now)
        assert start.hour == 9
        assert start.minute == 0
        assert start.second == 0
        assert start.microsecond == 0
