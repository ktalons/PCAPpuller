"""Unit tests for pcappuller.clean_cli: arg parsing, tool preflight, and clean_pipeline."""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest

import pcappuller.clean_cli as clean_cli
from pcappuller.errors import PCAPPullerError, ToolNotFoundError


def _run_pipeline(input_path: Path, out_dir: Path, **overrides):
    kwargs = dict(
        input_path=input_path,
        out_dir=out_dir,
        keep_format=False,
        do_reorder=True,
        snaplen=0,
        start_dt=None,
        end_dt=None,
        display_filter=None,
        split_seconds=None,
        split_packets=None,
        verbose=False,
    )
    kwargs.update(overrides)
    return clean_cli.clean_pipeline(**kwargs)


def test_parse_args_snaplen_default_zero(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["pcap-clean", "--input", "x.pcapng"])
    assert clean_cli.parse_args().snaplen == 0


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("x.pcap", ".pcap"),
        ("x.PCAP", ".pcap"),
        ("x.pcapng", ".pcapng"),
        ("x.cap", ".pcapng"),
    ],
)
def test_suffix_for(name, expected):
    assert clean_cli._suffix_for(Path(name)) == expected


def test_ensure_tools_all_present(fake_which):
    clean_cli.ensure_tools_for_clean(use_reorder=True, use_filter=True)


def test_ensure_tools_missing_editcap_always_raises(fake_which):
    fake_which.add("editcap")
    with pytest.raises(ToolNotFoundError):
        clean_cli.ensure_tools_for_clean(use_reorder=False, use_filter=False)


def test_ensure_tools_optional_tools_checked_only_when_used(fake_which):
    fake_which.update({"reordercap", "tshark"})
    clean_cli.ensure_tools_for_clean(use_reorder=False, use_filter=False)  # no raise
    with pytest.raises(ToolNotFoundError):
        clean_cli.ensure_tools_for_clean(use_reorder=True, use_filter=False)
    with pytest.raises(ToolNotFoundError):
        clean_cli.ensure_tools_for_clean(use_reorder=False, use_filter=True)


def test_default_flow_converts_then_reorders(tmp_path, fake_run, fake_which, make_minimal_pcap):
    """pcapng input: convert attempt, reorder, no snaplen/filter calls, single output."""
    src = make_minimal_pcap(tmp_path / "in.pcapng")
    out_dir = tmp_path / "clean"

    outs = _run_pipeline(src, out_dir)

    assert [Path(c[0]).name for c in fake_run.calls] == ["editcap", "reordercap"]
    convert = fake_run.argv_for("editcap")[0]
    assert convert[1:3] == ["-F", "pcap"]
    assert convert[-1] == str(out_dir / "in.pcap")
    assert not any("-s" in c for c in fake_run.argv_for("editcap"))
    assert not fake_run.argv_for("tshark")
    assert outs == [out_dir / "in.sorted.pcap"]
    assert outs[0].exists()


def test_snaplen_adds_editcap_s_call(tmp_path, fake_run, fake_which, make_minimal_pcap):
    """snaplen > 0 issues editcap -s with the current format passed as -F."""
    src = make_minimal_pcap(tmp_path / "in.pcapng")
    out_dir = tmp_path / "clean"

    outs = _run_pipeline(src, out_dir, keep_format=True, do_reorder=False, snaplen=256)

    (call,) = fake_run.argv_for("editcap")
    assert call[1:5] == ["-s", "256", "-F", "pcapng"]
    assert outs == [out_dir / "in.s256.pcapng"]
    assert outs[0].exists()


def test_missing_input_raises(tmp_path, fake_run, fake_which):
    with pytest.raises(PCAPPullerError, match="not found"):
        _run_pipeline(tmp_path / "nope.pcap", tmp_path / "clean")


def test_start_without_end_raises(tmp_path, fake_run, fake_which, make_minimal_pcap):
    src = make_minimal_pcap(tmp_path / "in.pcap")
    with pytest.raises(PCAPPullerError, match="both --start and --end"):
        _run_pipeline(
            src,
            tmp_path / "clean",
            keep_format=True,
            do_reorder=False,
            start_dt=dt.datetime(2026, 1, 1, 10, 0, 0),
        )


def test_split_packets_collects_underscore_chunks(
    tmp_path, fake_run, fake_which, make_minimal_pcap
):
    """editcap -c is invoked; only files matching base.chunk_* are collected as outputs."""
    src = make_minimal_pcap(tmp_path / "in.pcapng")
    out_dir = tmp_path / "clean"
    out_dir.mkdir()
    # Pre-create chunks the way real editcap names them (underscore + counter)
    chunks = [out_dir / "in.chunk_00001.pcapng", out_dir / "in.chunk_00002.pcapng"]
    for c in chunks:
        c.write_bytes(b"CHUNK")

    outs = _run_pipeline(src, out_dir, keep_format=True, do_reorder=False, split_packets=10)

    (call,) = fake_run.argv_for("editcap")
    assert call[1:3] == ["-c", "10"]
    assert call[-1] == str(out_dir / "in.chunk.pcapng")
    assert outs == chunks


def test_split_packets_no_matching_chunks_returns_empty(
    tmp_path, fake_run, fake_which, make_minimal_pcap
):
    """The recorder writes argv[-1] literally as in.chunk.pcapng, which does not match the
    base.chunk_* glob (real editcap inserts _NNNNN_ into the name, which does). Chunk
    collection therefore finds nothing: clean_pipeline trusts editcap's naming and
    silently returns an empty output list when no chunk files match."""
    src = make_minimal_pcap(tmp_path / "in.pcapng")
    out_dir = tmp_path / "clean"

    outs = _run_pipeline(src, out_dir, keep_format=True, do_reorder=False, split_packets=5)

    assert fake_run.argv_for("editcap")  # the split command did run
    assert outs == []
