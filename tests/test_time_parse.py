"""Unit tests for pcappuller.time_parse."""

from __future__ import annotations

import datetime as dt
import os
import time

import pytest

from pcappuller.errors import PCAPPullerError
from pcappuller.time_parse import TimeParseError, parse_dt_flexible, parse_start_and_window


@pytest.fixture
def phoenix_tz():
    """Pin local time to America/Phoenix (UTC-7, no DST) for Z-suffix conversion tests."""
    old = os.environ.get("TZ")
    os.environ["TZ"] = "America/Phoenix"
    time.tzset()
    yield
    if old is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = old
    time.tzset()


# --- parse_dt_flexible ---------------------------------------------------


def test_space_separator():
    assert parse_dt_flexible("2026-01-02 10:30:00") == dt.datetime(2026, 1, 2, 10, 30, 0)


def test_t_separator():
    assert parse_dt_flexible("2026-01-02T10:30:00") == dt.datetime(2026, 1, 2, 10, 30, 0)


def test_fractional_seconds():
    got = parse_dt_flexible("2026-01-02 10:30:00.250")
    assert got == dt.datetime(2026, 1, 2, 10, 30, 0, 250000)


def test_t_separator_with_fractional_seconds():
    got = parse_dt_flexible("2026-01-02T10:30:00.000123")
    assert got == dt.datetime(2026, 1, 2, 10, 30, 0, 123)


def test_surrounding_whitespace_stripped():
    assert parse_dt_flexible("  2026-01-02 10:30:00\n") == dt.datetime(2026, 1, 2, 10, 30, 0)


def test_z_suffix_converts_utc_to_local_naive(phoenix_tz):
    got = parse_dt_flexible("2026-01-02T12:00:00Z")
    assert got == dt.datetime(2026, 1, 2, 5, 0, 0)  # UTC-7
    assert got.tzinfo is None


def test_z_suffix_with_fractional_seconds(phoenix_tz):
    got = parse_dt_flexible("2026-01-02 12:00:00.500Z")
    assert got == dt.datetime(2026, 1, 2, 5, 0, 0, 500000)
    assert got.tzinfo is None


@pytest.mark.parametrize("bad", ["", "garbage", "2026-99-99 12:00:00", "not a date at all"])
def test_invalid_raises_time_parse_error(bad):
    with pytest.raises(TimeParseError):
        parse_dt_flexible(bad)


def test_time_parse_error_is_value_error_and_pcappuller_error():
    assert issubclass(TimeParseError, ValueError)
    assert issubclass(TimeParseError, PCAPPullerError)
    with pytest.raises(ValueError):
        parse_dt_flexible("garbage")
    with pytest.raises(PCAPPullerError):
        parse_dt_flexible("garbage")


# --- parse_start_and_window ----------------------------------------------


def test_neither_minutes_nor_end_raises():
    with pytest.raises(TimeParseError, match=r"Provide exactly one of --minutes or --end\."):
        parse_start_and_window("2026-01-02 10:00:00", None, None)


def test_both_minutes_and_end_raises():
    with pytest.raises(TimeParseError, match=r"Provide exactly one of --minutes or --end\."):
        parse_start_and_window("2026-01-02 10:00:00", 5, "2026-01-02 10:05:00")


def test_end_same_day_accepted():
    start, end = parse_start_and_window("2026-01-02 10:00:00", None, "2026-01-02 10:30:00")
    assert start == dt.datetime(2026, 1, 2, 10, 0, 0)
    assert end == dt.datetime(2026, 1, 2, 10, 30, 0)


def test_end_crossing_midnight_raises():
    with pytest.raises(TimeParseError, match="crosses midnight"):
        parse_start_and_window("2026-01-02 23:00:00", None, "2026-01-03 00:30:00")


def test_minutes_end_computation():
    start, end = parse_start_and_window("2026-01-02 10:00:00", 30, None)
    assert start == dt.datetime(2026, 1, 2, 10, 0, 0)
    assert end == dt.datetime(2026, 1, 2, 10, 30, 0)


def test_minutes_crossing_midnight_clamped():
    start, end = parse_start_and_window("2026-01-02 23:50:00", 30, None)
    assert start == dt.datetime(2026, 1, 2, 23, 50, 0)
    assert end == dt.datetime(2026, 1, 2, 23, 59, 59, 999999)


def test_minutes_landing_exactly_on_midnight_clamped():
    _, end = parse_start_and_window("2026-01-02 23:30:00", 30, None)
    assert end == dt.datetime(2026, 1, 2, 23, 59, 59, 999999)


def test_end_not_after_start_rejected():
    with pytest.raises(TimeParseError, match="after"):
        parse_start_and_window("2026-01-02 10:00:00", None, "2026-01-02 09:00:00")
    with pytest.raises(TimeParseError, match="after"):
        parse_start_and_window("2026-01-02 10:00:00", None, "2026-01-02 10:00:00")
