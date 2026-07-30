"""Unit tests for pcappuller.core: parse_workers, candidate_files, ensure_tools."""
from __future__ import annotations

import datetime as dt
import os

import pytest

from pcappuller.core import Window, candidate_files, ensure_tools, parse_workers
from pcappuller.errors import PCAPPullerError, ToolNotFoundError


def _utc(ts: float) -> dt.datetime:
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc)


WINDOW = Window(start=_utc(10_000), end=_utc(20_000))
SLOP_MIN = 10  # 600 s of slop on each side: [9400, 20600]


# ---------------------------------------------------------------- parse_workers

def test_parse_workers_auto_scales_with_cpu(monkeypatch):
    """auto -> 2x cores."""
    monkeypatch.setattr(os, "cpu_count", lambda: 8)
    assert parse_workers("auto", total_files=10) == 16


def test_parse_workers_auto_floor_is_four(monkeypatch):
    monkeypatch.setattr(os, "cpu_count", lambda: 1)
    assert parse_workers("auto", 10) == 4


def test_parse_workers_auto_cpu_count_none_defaults_to_four_cores(monkeypatch):
    monkeypatch.setattr(os, "cpu_count", lambda: None)
    assert parse_workers("auto", 10) == 8


def test_parse_workers_auto_caps_by_set_size(monkeypatch):
    """Big cpu counts cap at 32 normally, 16 for very large file sets."""
    monkeypatch.setattr(os, "cpu_count", lambda: 32)
    assert parse_workers("auto", 10) == 32
    assert parse_workers("auto", 1999) == 32
    assert parse_workers("auto", 2000) == 16


def test_parse_workers_auto_is_case_and_space_insensitive(monkeypatch):
    monkeypatch.setattr(os, "cpu_count", lambda: 8)
    assert parse_workers(" AUTO ", 10) == 16


def test_parse_workers_integer_strings():
    assert parse_workers("8", 10) == 8
    assert parse_workers(" 12 ", 10) == 12


def test_parse_workers_string_bounds_clamped():
    assert parse_workers("0", 10) == 1
    assert parse_workers("-5", 10) == 1
    assert parse_workers("999", 10) == 64


def test_parse_workers_int_passthrough_and_clamped():
    assert parse_workers(7, 10) == 7
    assert parse_workers(1, 10) == 1
    assert parse_workers(64, 10) == 64
    assert parse_workers(0, 10) == 1
    assert parse_workers(-3, 10) == 1
    assert parse_workers(100, 10) == 64


@pytest.mark.parametrize("bad", ["banana", "3.5", "", "auto8"])
def test_parse_workers_invalid_raises(bad):
    with pytest.raises(PCAPPullerError, match="Invalid --workers"):
        parse_workers(bad, 10)


# -------------------------------------------------------------- candidate_files

def test_candidate_files_mtime_window_and_extensions(pcap_tree):
    root = pcap_tree(
        [
            ("in.pcap", 15_000),
            ("edge_low.pcap", 9_400),  # exactly start - slop: inclusive
            ("edge_high.pcapng", 20_600),  # exactly end + slop: inclusive
            ("below.pcap", 9_399),
            ("above.cap", 20_601),
            ("in_window.cap", 15_000),
            ("notes.txt", 15_000),  # wrong extension, right mtime
            ("sub/nested.pcapng", 15_000),  # recursion into subdirs
            ("upper.PCAP", 15_000),  # extension match is case-insensitive
        ]
    )
    got = {p.relative_to(root).as_posix() for p in candidate_files([root], WINDOW, SLOP_MIN)}
    assert got == {
        "in.pcap",
        "edge_low.pcap",
        "edge_high.pcapng",
        "in_window.cap",
        "sub/nested.pcapng",
        "upper.PCAP",
    }


def test_candidate_files_non_directory_root_raises(tmp_path):
    file_root = tmp_path / "not_a_dir.pcap"
    file_root.write_bytes(b"x")
    with pytest.raises(PCAPPullerError, match="not a directory"):
        candidate_files([file_root], WINDOW, SLOP_MIN)
    with pytest.raises(PCAPPullerError, match="not a directory"):
        candidate_files([tmp_path / "missing"], WINDOW, SLOP_MIN)


def test_candidate_files_progress_phases(pcap_tree):
    # Exactly 200 files in one directory triggers the seen % 200 heartbeat.
    root = pcap_tree([(f"f{i:03d}.pcap", 15_000) for i in range(200)])
    phases: list[tuple[str, int, int]] = []
    files = candidate_files([root], WINDOW, SLOP_MIN, progress=lambda *a: phases.append(a))
    assert len(files) == 200
    assert phases[0] == ("scan-start", 0, 0)
    assert ("scan", 200, 0) in phases
    assert phases[-1] == ("scan-done", 200, 200)


def test_candidate_files_raising_progress_callback_is_swallowed(pcap_tree):
    root = pcap_tree([(f"f{i:03d}.pcap", 15_000) for i in range(200)])
    calls = {"n": 0}

    def bad(phase: str, cur: int, total: int) -> None:
        calls["n"] += 1
        raise RuntimeError("progress callback boom")

    files = candidate_files([root], WINDOW, SLOP_MIN, progress=bad)
    assert len(files) == 200
    assert calls["n"] >= 3  # scan-start, heartbeat, scan-done all attempted


# ----------------------------------------------------------------- ensure_tools

def test_ensure_tools_all_present(fake_which):
    ensure_tools(display_filter="tcp", precise_filter=True)  # must not raise


def test_ensure_tools_missing_mergecap(fake_which):
    fake_which.add("mergecap")
    with pytest.raises(ToolNotFoundError, match="mergecap"):
        ensure_tools(display_filter=None, precise_filter=False)


def test_ensure_tools_capinfos_only_required_for_precise(fake_which):
    fake_which.add("capinfos")
    ensure_tools(display_filter=None, precise_filter=False)  # not needed: ok
    with pytest.raises(ToolNotFoundError, match="capinfos"):
        ensure_tools(display_filter=None, precise_filter=True)


def test_ensure_tools_tshark_only_required_for_display_filter(fake_which):
    fake_which.add("tshark")
    ensure_tools(display_filter=None, precise_filter=True)  # not needed: ok
    with pytest.raises(ToolNotFoundError, match="tshark"):
        ensure_tools(display_filter="tcp.port == 443", precise_filter=False)
