"""Unit tests for WorkflowState persistence (pcappuller.workflow)."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from pcappuller.core import Window
from pcappuller.errors import PCAPPullerError
from pcappuller.workflow import STATE_SCHEMA_VERSION, WorkflowState


def _make_state(tmp_path: Path, *, optionals: bool) -> WorkflowState:
    """Build a WorkflowState with optional fields either set or left None."""
    window = Window(
        start=dt.datetime(2026, 7, 1, 8, 30, 15, 123456),
        end=dt.datetime(2026, 7, 1, 12, 0, 0),
    )
    kwargs = {}
    if optionals:
        kwargs = {
            "selected_files": [tmp_path / "a.pcap", tmp_path / "sub" / "b.pcapng"],
            "processed_file": tmp_path / "merged.pcapng",
            "cleaned_file": tmp_path / "cleaned.pcap.gz",
            "step1_complete": True,
            "step2_complete": True,
            "step3_complete": True,
        }
    return WorkflowState(
        workspace_dir=tmp_path / "ws",
        root_dirs=[tmp_path / "r1", tmp_path / "r2"],
        window=window,
        include_patterns=["*.pcap", "core_*"],
        exclude_patterns=["*old*"],
        **kwargs,
    )


@pytest.mark.parametrize("optionals", [False, True])
def test_save_load_roundtrip(tmp_path, optionals):
    """Roundtrip preserves paths, window datetimes, patterns, flags, optionals."""
    state = _make_state(tmp_path, optionals=optionals)
    state_file = tmp_path / "workflow_state.json"
    state.save(state_file)
    loaded = WorkflowState.load(state_file)
    assert loaded == state


def test_save_is_atomic_no_tmp_left(tmp_path):
    """After a successful save, no *.tmp sibling remains."""
    state = _make_state(tmp_path, optionals=False)
    state_file = tmp_path / "workflow_state.json"
    state.save(state_file)
    assert state_file.exists()
    assert list(tmp_path.glob("*.tmp")) == []


def test_save_crash_mid_write_keeps_original(tmp_path, monkeypatch):
    """A failure during json.dump must not clobber the existing state file."""
    state = _make_state(tmp_path, optionals=False)
    state_file = tmp_path / "workflow_state.json"
    state.save(state_file)
    original = state_file.read_bytes()

    def boom(obj, fh, **kwargs):
        fh.write('{"partial": ')
        raise RuntimeError("simulated crash mid-write")

    monkeypatch.setattr(json, "dump", boom)
    state.step1_complete = True
    with pytest.raises(RuntimeError, match="mid-write"):
        state.save(state_file)
    assert state_file.read_bytes() == original
    assert WorkflowState.load(state_file) == _make_state(tmp_path, optionals=False)


def test_saved_json_contains_schema_version(tmp_path):
    state = _make_state(tmp_path, optionals=False)
    state_file = tmp_path / "workflow_state.json"
    state.save(state_file)
    data = json.loads(state_file.read_text())
    assert data["schema_version"] == 1 == STATE_SCHEMA_VERSION


def test_load_without_schema_version_is_legacy_ok(tmp_path):
    """Pre-schema files (no schema_version key) load as v1."""
    state = _make_state(tmp_path, optionals=True)
    state_file = tmp_path / "workflow_state.json"
    state.save(state_file)
    data = json.loads(state_file.read_text())
    del data["schema_version"]
    state_file.write_text(json.dumps(data))
    assert WorkflowState.load(state_file) == state


def test_load_newer_schema_version_raises(tmp_path):
    state = _make_state(tmp_path, optionals=False)
    state_file = tmp_path / "workflow_state.json"
    state.save(state_file)
    data = json.loads(state_file.read_text())
    data["schema_version"] = 99
    state_file.write_text(json.dumps(data))
    with pytest.raises(PCAPPullerError, match="newer"):
        WorkflowState.load(state_file)


def test_load_ignores_unknown_extra_key(tmp_path):
    state = _make_state(tmp_path, optionals=False)
    state_file = tmp_path / "workflow_state.json"
    state.save(state_file)
    data = json.loads(state_file.read_text())
    data["future_field"] = 1
    state_file.write_text(json.dumps(data))
    loaded = WorkflowState.load(state_file)
    assert loaded == state
    assert not hasattr(loaded, "future_field")
