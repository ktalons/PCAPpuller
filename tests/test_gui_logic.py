"""Headless tests for pure-logic pieces of pcappuller.gui (no window opened)."""

from __future__ import annotations

import json
import os
import time

import pytest

pytest.importorskip("FreeSimpleGUI")

import pcappuller.gui as gui  # noqa: E402


def _ws(tmp, name, age_days=10, sentinel=True, state="{}"):
    d = tmp / name
    d.mkdir()
    (d / "workflow_state.json").write_text(state)
    if sentinel:
        (d / gui.AUTOTMP_SENTINEL).touch()
    old = time.time() - age_days * 86400
    os.utime(d, (old, old))
    return d


def test_sweep_removes_only_sentineled_stale_pattern_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(gui.tempfile, "gettempdir", lambda: str(tmp_path))
    stale = _ws(tmp_path, "pcappuller_20260101_101010")
    fresh = _ws(tmp_path, "pcappuller_20260102_101010", age_days=1)
    manual = _ws(tmp_path, "pcappuller_caseA")  # user-named: pattern mismatch
    nosent = _ws(tmp_path, "pcappuller_20260103_101010", sentinel=False)
    gui._sweep_stale_workspaces()
    assert not stale.exists()
    assert fresh.exists()
    assert manual.exists()
    assert nosent.exists()


def test_sweep_keeps_workspace_holding_output(tmp_path, monkeypatch):
    """A stale auto-workspace whose state names a live artifact inside it survives."""
    monkeypatch.setattr(gui.tempfile, "gettempdir", lambda: str(tmp_path))
    d = tmp_path / "pcappuller_20260101_090909"
    d.mkdir()
    out = d / "cleaned" / "final.pcap"
    out.parent.mkdir(parents=True)
    out.write_bytes(b"x")
    (d / "workflow_state.json").write_text(json.dumps({"cleaned_file": str(out)}))
    (d / gui.AUTOTMP_SENTINEL).touch()
    old = time.time() - 30 * 86400
    os.utime(d, (old, old))
    gui._sweep_stale_workspaces()
    assert d.exists()
    assert out.exists()
