"""Unit tests for pcappuller.tools — subprocess boundary faked, no Wireshark tools run."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

import pcappuller.tools as tools
from pcappuller.errors import ExternalToolError, ToolNotFoundError


def _fake_run(monkeypatch, *, returncode=0, stdout="", stderr="", exc=None):
    """Monkeypatch subprocess.run; returns a dict capturing the last call."""
    captured: dict = {}

    def run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        if exc is not None:
            raise exc
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(subprocess, "run", run)
    return captured


# --- capinfos_epoch_bounds ---


def test_capinfos_parses_first_last_labels(monkeypatch):
    """'First/Last packet time:' labels parse to epoch floats."""
    out = "First packet time:   1700000000.123456\nLast packet time:    1700000100.654321\n"
    captured = _fake_run(monkeypatch, stdout=out)
    first, last = tools.capinfos_epoch_bounds(Path("/x/a.pcap"))
    assert first == pytest.approx(1700000000.123456)
    assert last == pytest.approx(1700000100.654321)
    assert captured["cmd"][0] == "capinfos"


def test_capinfos_parses_earliest_latest_labels(monkeypatch):
    """'Earliest/Latest packet time:' labels are equally accepted."""
    out = "Earliest packet time: 1600000000.5\nLatest packet time:   1600000001.5\n"
    _fake_run(monkeypatch, stdout=out)
    assert tools.capinfos_epoch_bounds(Path("a.pcap")) == (1600000000.5, 1600000001.5)


def test_capinfos_garbage_values_give_none(monkeypatch):
    """Unparseable time values fall back to None per field."""
    out = "First packet time:   n/a\nLast packet time:    2023-01-01 00:00:00\n"
    _fake_run(monkeypatch, stdout=out)
    assert tools.capinfos_epoch_bounds(Path("a.pcap")) == (None, None)


def test_capinfos_nonzero_rc_gives_none_none(monkeypatch):
    _fake_run(monkeypatch, returncode=1, stdout="First packet time: 1.0\n")
    assert tools.capinfos_epoch_bounds(Path("a.pcap")) == (None, None)


def test_capinfos_timeout_gives_none_none(monkeypatch):
    exc = subprocess.TimeoutExpired(cmd=["capinfos"], timeout=tools.CAPINFOS_TIMEOUT_S)
    _fake_run(monkeypatch, exc=exc)
    assert tools.capinfos_epoch_bounds(Path("a.pcap")) == (None, None)


def test_capinfos_passes_timeout_60(monkeypatch):
    captured = _fake_run(monkeypatch, stdout="")
    tools.capinfos_epoch_bounds(Path("a.pcap"))
    assert captured["kwargs"]["timeout"] == 60
    assert captured["kwargs"]["timeout"] == tools.CAPINFOS_TIMEOUT_S


# --- which_or_error ---


def test_which_or_error_found(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: f"/opt/bin/{name}")
    assert tools.which_or_error("mergecap") == "/opt/bin/mergecap"


def test_which_or_error_missing_raises(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(ToolNotFoundError, match="mergecap"):
        tools.which_or_error("mergecap")


# --- _run ---


def test_run_nonzero_raises_external_tool_error(monkeypatch):
    _fake_run(monkeypatch, returncode=2, stderr="line1\nbad magic number\n")
    with pytest.raises(ExternalToolError) as ei:
        tools._run(["editcap", "-F", "pcap", "src", "dst"])
    msg = str(ei.value)
    assert "editcap" in msg
    assert "2" in msg
    assert "bad magic number" in msg


def test_run_file_not_found_raises_tool_not_found(monkeypatch):
    _fake_run(monkeypatch, exc=FileNotFoundError("no such file"))
    with pytest.raises(ToolNotFoundError, match="mergecap"):
        tools._run(["mergecap", "-w", "out.pcap"])


def test_run_zero_rc_no_raise(monkeypatch):
    _fake_run(monkeypatch, returncode=0, stderr="harmless warning")
    tools._run(["mergecap", "-w", "out.pcap"])  # must not raise


# --- try_convert_to_pcap ---


def test_try_convert_failure_unlinks_partial_dst(monkeypatch, tmp_path):
    dst = tmp_path / "out.pcap"

    def failing_run(cmd, verbose=False):
        dst.write_bytes(b"partial")  # simulate a partially written output
        raise ExternalToolError("editcap", 2, "multiple link types")

    monkeypatch.setattr(tools, "_run", failing_run)
    assert tools.try_convert_to_pcap(tmp_path / "src.pcapng", dst) is False
    assert not dst.exists()


def test_try_convert_success_returns_true(monkeypatch, tmp_path):
    dst = tmp_path / "out.pcap"

    def ok_run(cmd, verbose=False):
        dst.write_bytes(b"converted")

    monkeypatch.setattr(tools, "_run", ok_run)
    assert tools.try_convert_to_pcap(tmp_path / "src.pcapng", dst) is True
    assert dst.exists()
