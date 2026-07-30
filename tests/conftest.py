"""Shared fixtures for the PCAPpuller test suite.

Every test is pure-unit: no Wireshark tools are invoked. Subprocess calls
are faked at the pcappuller.tools boundary, and pcap files are minimal
hand-written byte structures.
"""

from __future__ import annotations

import struct
import time
from pathlib import Path

import pytest

# Little-endian pcap global header: magic, v2.4, tz 0, sigfigs 0, snaplen 65535, linktype 1
_PCAP_GLOBAL_HEADER = struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)


def _pcap_record(ts_sec: int, payload: bytes = b"\x00" * 42) -> bytes:
    return struct.pack("<IIII", ts_sec, 0, len(payload), len(payload)) + payload


@pytest.fixture
def make_minimal_pcap():
    """Write a structurally valid single-packet pcap file (no tools needed)."""

    def _make(path: Path, ts_sec: int | None = None) -> Path:
        ts = int(time.time()) if ts_sec is None else ts_sec
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_PCAP_GLOBAL_HEADER + _pcap_record(ts))
        return path

    return _make


@pytest.fixture
def pcap_tree(tmp_path, make_minimal_pcap):
    """Build a directory of pcap files with controlled mtimes.

    Usage: pcap_tree([("a.pcap", mtime_epoch), ("sub/b.pcapng", mtime_epoch)])
    Returns the root directory.
    """

    def _build(entries: list[tuple[str, float]]) -> Path:
        root = tmp_path / "captures"
        root.mkdir(exist_ok=True)
        for rel, mtime in entries:
            p = root / rel
            make_minimal_pcap(p)
            import os

            os.utime(p, (mtime, mtime))
        return root

    return _build


class RunRecorder:
    """Stands in for pcappuller.tools._run: records argv, simulates outputs.

    Tool commands name an output file in a tool-specific argv position; the
    recorder touches that file so downstream code sees it exist.
    """

    def __init__(self):
        self.calls: list[list[str]] = []
        self.fail_on: str | None = None  # tool name that should raise

    def __call__(self, cmd, verbose: bool = False) -> None:
        from pcappuller.errors import ExternalToolError

        argv = [str(c) for c in cmd]
        self.calls.append(argv)
        tool = Path(argv[0]).name
        if self.fail_on == tool:
            raise ExternalToolError(tool, 2, "simulated failure")
        out = self._output_path(argv)
        if out is not None:
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            Path(out).write_bytes(b"FAKE" + tool.encode())

    @staticmethod
    def _output_path(argv: list[str]) -> str | None:
        tool = Path(argv[0]).name
        if tool == "mergecap":  # mergecap -w OUT inputs...
            return argv[argv.index("-w") + 1]
        if tool in ("editcap", "reordercap"):  # ... SRC DST
            return argv[-1]
        if tool == "tshark":  # tshark -r SRC -Y f -w OUT [-F fmt]
            return argv[argv.index("-w") + 1]
        return None

    def argv_for(self, tool: str) -> list[list[str]]:
        return [a for a in self.calls if Path(a[0]).name == tool]


@pytest.fixture
def fake_run(monkeypatch):
    """Replace tools._run with a RunRecorder across every import site."""
    rec = RunRecorder()
    import pcappuller.core as core
    import pcappuller.tools as tools

    monkeypatch.setattr(tools, "_run", rec)
    # core imports the wrappers, not _run, so patching tools._run covers it;
    # clean_cli imports _run directly and needs its own patch
    import pcappuller.clean_cli as clean_cli

    monkeypatch.setattr(clean_cli, "_run", rec)
    assert core  # silence unused-import lint
    return rec


@pytest.fixture
def fake_which(monkeypatch):
    """Make every tool lookup succeed (or fail for names in `missing`)."""
    missing: set[str] = set()

    def _which(name: str):
        return None if name in missing else f"/usr/bin/{name}"

    import shutil

    monkeypatch.setattr(shutil, "which", _which)
    return missing


@pytest.fixture
def fake_capinfos(monkeypatch):
    """Replace capinfos_epoch_bounds with a dict lookup: path name -> (first, last)."""
    bounds: dict[str, tuple[float | None, float | None]] = {}

    def _bounds(path: Path):
        return bounds.get(Path(path).name, (None, None))

    import pcappuller.core as core

    monkeypatch.setattr(core, "capinfos_epoch_bounds", _bounds)
    return bounds
