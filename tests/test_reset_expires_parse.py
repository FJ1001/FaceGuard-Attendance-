"""Reset token expiry parsing (SQLite formats)."""

from datetime import datetime

from database.user_repository import _parse_reset_expires


def test_parse_iso_seconds():
    s = "2026-12-31T15:30:00"
    d = _parse_reset_expires(s)
    assert d is not None
    assert d.year == 2026 and d.month == 12


def test_parse_sqlite_space():
    d = _parse_reset_expires("2026-04-12 10:00:00")
    assert d is not None
    assert d.hour == 10


def test_parse_datetime_passthrough():
    now = datetime(2026, 1, 1, 12, 0, 0)
    assert _parse_reset_expires(now) is now
