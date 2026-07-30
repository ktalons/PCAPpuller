from __future__ import annotations

import datetime as dt
import logging
from typing import TYPE_CHECKING, Optional, Tuple

from .errors import PCAPPullerError

if TYPE_CHECKING:
    from dateutil import parser as dateutil_parser
else:
    try:
        from dateutil import parser as dateutil_parser  # optional
    except Exception:
        dateutil_parser = None


class TimeParseError(PCAPPullerError, ValueError):
    pass


def parse_dt_flexible(s: str) -> dt.datetime:
    s = s.strip().replace("T", " ")
    # Try strict formats first
    fmts = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
    )
    for fmt in fmts:
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            pass
    # Z suffix (UTC)
    if s.endswith("Z"):
        s2 = s[:-1]
        for fmt in fmts:
            try:
                return (
                    dt.datetime.strptime(s2, fmt)
                    .replace(tzinfo=dt.timezone.utc)
                    .astimezone(tz=None)
                    .replace(tzinfo=None)
                )
            except ValueError:
                pass
    # Fallback: dateutil if available
    if dateutil_parser is not None:
        try:
            dv: dt.datetime = dateutil_parser.parse(s)
            if dv.tzinfo:
                return dv.astimezone(tz=None).replace(tzinfo=None)
            return dv
        except Exception:
            pass
    raise TimeParseError(f"Invalid datetime format: {s}. Use 'YYYY-MM-DD HH:MM:SS' or ISO-like.")


def parse_start_and_window(
    start_str: str, minutes: Optional[int], end_str: Optional[str]
) -> Tuple[dt.datetime, dt.datetime]:
    if (minutes is None) == (end_str is None):
        raise TimeParseError("Provide exactly one of --minutes or --end.")
    start = parse_dt_flexible(start_str)
    if end_str:
        end = parse_dt_flexible(end_str)
        if end.date() != start.date():
            raise TimeParseError(
                "Window crosses midnight. Choose a window within a single calendar day."
            )
        if end <= start:
            raise TimeParseError("--end must be after --start.")
    else:
        assert minutes is not None
        mins = int(minutes)
        end = start + dt.timedelta(minutes=mins)
        # Clamp to end-of-day if duration crosses midnight -- and say so, since
        # this silently narrows the requested evidence window
        if end.date() != start.date():
            clamped = dt.datetime.combine(start.date(), dt.time(23, 59, 59, 999999))
            logging.warning(
                "Window clamped to end of day: requested end %s, using %s. "
                "Run again with --start at midnight to cover the remainder.",
                end,
                clamped,
            )
            end = clamped
    return start, end
