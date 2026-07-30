"""Unit tests for pcappuller.core.precise_filter_parallel."""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

import pytest

import pcappuller.core as core
from pcappuller.core import Window, precise_filter_parallel
from pcappuller.errors import PCAPPullerError


def _utc(ts: float) -> dt.datetime:
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc)


WINDOW = Window(start=_utc(1_000), end=_utc(2_000))


def _paths(tmp_path: Path, *names: str) -> list[Path]:
    # Paths need not exist: capinfos_epoch_bounds is faked at the core boundary.
    return [tmp_path / n for n in names]


class FakeCache:
    """Duck-typed CapinfosCache: dict-backed get/set keyed by file name."""

    def __init__(self, preloaded: dict[str, tuple[float, float]] | None = None):
        self.preloaded = dict(preloaded or {})
        self.get_calls: list[str] = []
        self.set_calls: list[tuple[str, float | None, float | None]] = []

    def get(self, path: Path):
        self.get_calls.append(Path(path).name)
        return self.preloaded.get(Path(path).name)

    def set(self, path: Path, first, last) -> None:
        self.set_calls.append((Path(path).name, first, last))


def test_overlapping_kept_nonoverlapping_dropped(tmp_path, fake_capinfos):
    fake_capinfos.update(
        {
            "inside.pcap": (1_200.0, 1_800.0),
            "spans.pcap": (500.0, 2_500.0),
            "before.pcap": (100.0, 900.0),
            "after.pcap": (2_100.0, 3_000.0),
        }
    )
    files = _paths(tmp_path, "inside.pcap", "spans.pcap", "before.pcap", "after.pcap")
    prog: list[tuple[str, int, int]] = []
    kept = precise_filter_parallel(files, WINDOW, workers=2, progress=lambda *a: prog.append(a))
    assert {p.name for p in kept} == {"inside.pcap", "spans.pcap"}
    assert prog[-1] == ("precise", 4, 4)  # one progress tick per file


def test_boundary_touching_is_kept(tmp_path, fake_capinfos):
    """Closed-interval overlap: touching either window edge keeps the file."""
    fake_capinfos.update(
        {
            "ends_at_start.pcap": (500.0, 1_000.0),  # last == window start
            "starts_at_end.pcap": (2_000.0, 2_500.0),  # first == window end
        }
    )
    files = _paths(tmp_path, "ends_at_start.pcap", "starts_at_end.pcap")
    kept = precise_filter_parallel(files, WINDOW, workers=1)
    assert {p.name for p in kept} == {"ends_at_start.pcap", "starts_at_end.pcap"}


def test_unreadable_files_counted_as_failures(tmp_path, fake_capinfos, caplog):
    fake_capinfos["good.pcap"] = (1_500.0, 1_600.0)
    files = _paths(tmp_path, "good.pcap", "broken.pcap")  # broken -> (None, None)
    with caplog.at_level(logging.WARNING):
        kept = precise_filter_parallel(files, WINDOW, workers=2)
    assert [p.name for p in kept] == ["good.pcap"]
    assert "1 of 2" in caplog.text


def test_all_failures_raises_mentioning_capinfos(tmp_path, fake_capinfos):
    files = _paths(tmp_path, "a.pcap", "b.pcap")  # no bounds registered -> all fail
    with pytest.raises(PCAPPullerError, match="capinfos failed on 2 of 2"):
        precise_filter_parallel(files, WINDOW, workers=2)


def test_empty_kept_with_zero_failures_returns_empty(tmp_path, fake_capinfos):
    fake_capinfos.update(
        {
            "before.pcap": (100.0, 900.0),
            "after.pcap": (2_100.0, 2_200.0),
        }
    )
    files = _paths(tmp_path, "before.pcap", "after.pcap")
    assert precise_filter_parallel(files, WINDOW, workers=1) == []


def test_empty_input_returns_empty():
    assert precise_filter_parallel([], WINDOW, workers=1) == []


def test_cache_hit_short_circuits_capinfos(tmp_path, monkeypatch):
    def boom(path):
        raise AssertionError(f"capinfos_epoch_bounds called for {path}")

    monkeypatch.setattr(core, "capinfos_epoch_bounds", boom)
    cache = FakeCache({"hit.pcap": (1_100.0, 1_900.0)})
    kept = precise_filter_parallel([tmp_path / "hit.pcap"], WINDOW, workers=1, cache=cache)
    assert [p.name for p in kept] == ["hit.pcap"]
    assert cache.get_calls == ["hit.pcap"]
    assert cache.set_calls == []  # hits are not re-stored


def test_cache_miss_falls_through_and_populates(tmp_path, fake_capinfos):
    fake_capinfos["miss.pcap"] = (1_100.0, 1_900.0)
    cache = FakeCache()
    kept = precise_filter_parallel([tmp_path / "miss.pcap"], WINDOW, workers=1, cache=cache)
    assert [p.name for p in kept] == ["miss.pcap"]
    assert cache.set_calls == [("miss.pcap", 1_100.0, 1_900.0)]
