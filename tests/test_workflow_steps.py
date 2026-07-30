"""Unit tests for ThreeStepWorkflow (pcappuller.workflow)."""

from __future__ import annotations

import datetime as dt
import gzip
import json
from pathlib import Path

import pytest

from pcappuller.core import Window
from pcappuller.errors import PCAPPullerError
from pcappuller.workflow import ThreeStepWorkflow, WorkflowState

_BASE = 1_700_000_000  # arbitrary fixed epoch for mtime-window tests


def _window_from_epochs(start: float, end: float) -> Window:
    return Window(start=dt.datetime.fromtimestamp(start), end=dt.datetime.fromtimestamp(end))


def _forge_step2_state(
    tmp_path: Path, name: str = "merged.pcapng", content: bytes = b"FAKE-PCAP-BYTES"
) -> tuple[ThreeStepWorkflow, WorkflowState, Path]:
    """Build a workflow whose state pretends steps 1 and 2 already ran."""
    workflow = ThreeStepWorkflow(tmp_path / "workspace")
    processed = workflow.processed_dir / name
    processed.parent.mkdir(parents=True, exist_ok=True)
    processed.write_bytes(content)
    state = WorkflowState(
        workspace_dir=workflow.workspace_dir,
        root_dirs=[],
        window=_window_from_epochs(_BASE, _BASE + 3600),
        include_patterns=[],
        exclude_patterns=[],
        processed_file=processed,
        step1_complete=True,
        step2_complete=True,
    )
    return workflow, state, processed


def test_initialize_workflow_writes_state_file(tmp_path):
    workflow = ThreeStepWorkflow(tmp_path / "workspace")
    state = workflow.initialize_workflow(
        root_dirs=[tmp_path / "caps"],
        window=_window_from_epochs(_BASE, _BASE + 3600),
        include_patterns=["*.pcap"],
    )
    assert workflow.state_file.exists()
    data = json.loads(workflow.state_file.read_text())
    assert data["schema_version"] == 1
    assert not state.step1_complete


def test_load_workflow_without_state_raises(tmp_path):
    workflow = ThreeStepWorkflow(tmp_path / "workspace")
    with pytest.raises(PCAPPullerError, match="No workflow state"):
        workflow.load_workflow()


def test_step2_before_step1_raises(tmp_path):
    workflow = ThreeStepWorkflow(tmp_path / "workspace")
    state = workflow.initialize_workflow([tmp_path], _window_from_epochs(_BASE, _BASE + 3600))
    with pytest.raises(PCAPPullerError, match="Step 1 must be completed"):
        workflow.step2_process(state)


def test_step1_manifest_selects_without_materializing(tmp_path, pcap_tree):
    """Manifest mode records original paths, creates no selected dir, saves state."""
    root = pcap_tree(
        [
            ("in_a.pcap", _BASE + 60),
            ("sub/in_b.pcapng", _BASE + 120),
            ("too_late.pcap", _BASE + 900_000),
        ]
    )
    workflow = ThreeStepWorkflow(tmp_path / "workspace")
    state = workflow.initialize_workflow([root], _window_from_epochs(_BASE, _BASE + 3600))
    result = workflow.step1_select_and_move(state, slop_min=0, selection_mode="manifest")

    assert sorted(p.name for p in result.selected_files) == ["in_a.pcap", "in_b.pcapng"]
    assert {p.parent for p in result.selected_files} <= {root, root / "sub"}
    assert not workflow.selected_dir.exists()
    assert result.step1_complete
    reloaded = workflow.load_workflow()
    assert reloaded.step1_complete
    assert sorted(reloaded.selected_files) == sorted(result.selected_files)


def test_apply_patterns_include_restricts(tmp_path):
    workflow = ThreeStepWorkflow(tmp_path / "workspace")
    files = [Path("a.pcap"), Path("b.pcapng"), Path("old_c.pcap")]
    assert workflow._apply_patterns(files, ["*.pcap"], []) == [
        Path("a.pcap"),
        Path("old_c.pcap"),
    ]


def test_apply_patterns_exclude_removes(tmp_path):
    workflow = ThreeStepWorkflow(tmp_path / "workspace")
    files = [Path("a.pcap"), Path("b.pcapng"), Path("old_c.pcap")]
    assert workflow._apply_patterns(files, [], ["old_*"]) == [Path("a.pcap"), Path("b.pcapng")]


def test_apply_patterns_include_and_exclude_combined(tmp_path):
    workflow = ThreeStepWorkflow(tmp_path / "workspace")
    files = [Path("a.pcap"), Path("b.pcapng"), Path("old_c.pcap")]
    assert workflow._apply_patterns(files, ["*.pcap"], ["old_*"]) == [Path("a.pcap")]


def test_apply_patterns_empty_include_means_no_filtering(tmp_path):
    workflow = ThreeStepWorkflow(tmp_path / "workspace")
    files = [Path("a.pcap"), Path("b.pcapng")]
    assert workflow._apply_patterns(files, [], []) == files


def test_step3_before_step2_raises(tmp_path):
    workflow = ThreeStepWorkflow(tmp_path / "workspace")
    state = workflow.initialize_workflow([tmp_path], _window_from_epochs(_BASE, _BASE + 3600))
    state.step1_complete = True
    with pytest.raises(PCAPPullerError, match="Step 2 must be completed"):
        workflow.step3_clean(state, {"gzip": True})


def test_step3_snaplen_passes_format_for_pcap_input(tmp_path, fake_run):
    """editcap gets -s N and -F pcap when the input is .pcap; output stays .pcap."""
    workflow, state, _ = _forge_step2_state(tmp_path, name="merged.pcap")
    result = workflow.step3_clean(state, {"snaplen": 96})

    calls = fake_run.argv_for("editcap")
    assert len(calls) == 1
    argv = calls[0]
    assert argv[argv.index("-s") + 1] == "96"
    assert argv[argv.index("-F") + 1] == "pcap"
    assert argv[-1].endswith(".pcap")
    assert result.cleaned_file.suffix == ".pcap"
    assert result.cleaned_file.name.startswith("snaplen_")
    assert result.cleaned_file.exists()
    assert result.step3_complete


def test_step3_convert_to_pcap_success(tmp_path, fake_run):
    workflow, state, _ = _forge_step2_state(tmp_path, name="merged.pcapng")
    result = workflow.step3_clean(state, {"convert_to_pcap": True})

    calls = fake_run.argv_for("editcap")
    assert len(calls) == 1
    argv = calls[0]
    assert argv[argv.index("-F") + 1] == "pcap"
    assert result.cleaned_file.suffix == ".pcap"
    assert result.cleaned_file.name.startswith("converted_")


def test_step3_convert_to_pcap_failure_keeps_original(tmp_path, fake_run, caplog):
    workflow, state, processed = _forge_step2_state(tmp_path, name="merged.pcapng")
    fake_run.fail_on = "editcap"
    with caplog.at_level("WARNING"):
        result = workflow.step3_clean(state, {"convert_to_pcap": True})

    assert result.cleaned_file == processed
    assert result.cleaned_file.suffix == ".pcapng"
    assert result.step3_complete
    assert any("Failed to convert to pcap" in r.message for r in caplog.records)


def test_step3_gzip_produces_real_gz(tmp_path):
    content = b"FAKE-PCAP-BYTES-FOR-GZIP"
    workflow, state, processed = _forge_step2_state(tmp_path, name="merged.pcap", content=content)
    result = workflow.step3_clean(state, {"gzip": True})

    assert result.cleaned_file == processed.with_suffix(".pcap.gz")
    assert result.cleaned_file.name.endswith(".gz")
    with gzip.open(result.cleaned_file, "rb") as fh:
        assert fh.read() == content
