"""Unit tests for pcappuller.cli: argument parsing, exit codes, and preflight wiring."""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest

import pcappuller.cli as cli
from pcappuller import __version__
from pcappuller.core import Window
from pcappuller.errors import PCAPPullerError, TempSpaceError, ToolNotFoundError
from pcappuller.time_parse import TimeParseError
from pcappuller.workflow import ThreeStepWorkflow

WINDOW = Window(start=dt.datetime(2026, 1, 1, 10, 0, 0), end=dt.datetime(2026, 1, 1, 10, 30, 0))


def _argv(monkeypatch, *args: str) -> None:
    monkeypatch.setattr(sys, "argv", ["pcap-puller", *args])


def _required_args(workspace: str = "ws", source: str = "src") -> list[str]:
    return [
        "--workspace",
        workspace,
        "--source",
        source,
        "--start",
        "2026-01-01 10:00:00",
        "--minutes",
        "30",
    ]


def test_version_prints_version_and_exits_zero(monkeypatch, capsys):
    """--version prints the package version to stdout and exits 0."""
    _argv(monkeypatch, "--version")
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_missing_workspace_exits_2(monkeypatch, capsys):
    """No --workspace is an argparse error: exit code 2."""
    _argv(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert "--workspace" in capsys.readouterr().err


def test_new_workflow_without_source_exits_2(monkeypatch, capsys, tmp_path):
    """A new (non-resume) workflow demands --source: exit code 2."""
    _argv(monkeypatch, "--workspace", str(tmp_path / "ws"))
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert "--source" in capsys.readouterr().err


@pytest.mark.parametrize("minutes", ["0", "1441"])
def test_minutes_out_of_range_exits_2(monkeypatch, capsys, minutes):
    """--minutes outside 1..1440 is rejected with exit code 2."""
    _argv(
        monkeypatch,
        "--workspace",
        "ws",
        "--source",
        "src",
        "--start",
        "2026-01-01 10:00:00",
        "--minutes",
        minutes,
    )
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert "--minutes" in capsys.readouterr().err


def test_minutes_and_end_mutually_exclusive(monkeypatch, capsys):
    """--minutes and --end share a mutually exclusive group: exit code 2."""
    _argv(
        monkeypatch,
        "--workspace",
        "ws",
        "--source",
        "src",
        "--start",
        "2026-01-01 10:00:00",
        "--minutes",
        "30",
        "--end",
        "2026-01-01 11:00:00",
    )
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert "not allowed with" in capsys.readouterr().err


def test_trim_per_batch_default_is_none(monkeypatch):
    """Neither trim flag: tri-state stays None (auto)."""
    _argv(monkeypatch, *_required_args())
    assert cli.parse_args().trim_per_batch is None


def test_trim_per_batch_flag_true(monkeypatch):
    _argv(monkeypatch, *_required_args(), "--trim-per-batch")
    assert cli.parse_args().trim_per_batch is True


def test_no_trim_per_batch_flag_false(monkeypatch):
    _argv(monkeypatch, *_required_args(), "--no-trim-per-batch")
    assert cli.parse_args().trim_per_batch is False


def test_status_output_is_ascii(monkeypatch, capsys, tmp_path):
    """--status on a fresh workspace prints pure-ASCII output and exits 0."""
    ws = tmp_path / "ws"
    workflow = ThreeStepWorkflow(ws)
    workflow.initialize_workflow(root_dirs=[tmp_path], window=WINDOW)

    _argv(monkeypatch, "--workspace", str(ws), "--status")
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "Workflow status" in out
    assert all(ord(c) < 128 for c in out)


def test_exit_code_mapping():
    assert cli._exit_code_for(TimeParseError("bad time")) == 3
    assert cli._exit_code_for(TempSpaceError("disk full")) == 10
    assert cli._exit_code_for(ToolNotFoundError("no mergecap")) == 11
    assert cli._exit_code_for(PCAPPullerError("generic")) == 11


def test_final_out_path_adopts_cleaned_extension_chain():
    got = cli._final_out_path(Path("/data/final.pcapng"), Path("x.pcap.gz"))
    assert got == Path("/data/final.pcap.gz")


def test_final_out_path_keeps_matching_suffix():
    got = cli._final_out_path(Path("/data/final.pcapng"), Path("y.pcapng"))
    assert got == Path("/data/final.pcapng")


def test_final_out_path_out_without_suffix():
    got = cli._final_out_path(Path("/data/final"), Path("x.pcap.gz"))
    assert got == Path("/data/final.pcap.gz")


def test_final_out_path_preserves_dotted_stems():
    """IP- and date-named targets must keep their stem intact (audit finding)."""
    got = cli._final_out_path(Path("/data/10.0.0.1_capture.pcapng"), Path("c.pcap"))
    assert got == Path("/data/10.0.0.1_capture.pcap")
    got = cli._final_out_path(Path("/data/incident.2026-07-30.pcapng"), Path("c.pcap.gz"))
    assert got == Path("/data/incident.2026-07-30.pcap.gz")
    got = cli._final_out_path(Path("/data/v1.2.3-capture.pcapng"), Path("c.pcapng"))
    assert got == Path("/data/v1.2.3-capture.pcapng")


def test_final_out_path_ignores_unknown_cleaned_suffixes():
    got = cli._final_out_path(Path("/data/final.pcapng"), Path("snaplen_2026.01.15.pcap"))
    assert got == Path("/data/final.pcap")


def test_step2_preflight_missing_mergecap_exits_11(
    monkeypatch, tmp_path, fake_which, make_minimal_pcap
):
    """Preflight for --step 2 runs ensure_tools before any work: missing mergecap -> 11."""
    fake_which.add("mergecap")

    ws = tmp_path / "ws"
    workflow = ThreeStepWorkflow(ws)
    state = workflow.initialize_workflow(root_dirs=[tmp_path], window=WINDOW)
    state.selected_files = [make_minimal_pcap(tmp_path / "a.pcap")]
    state.step1_complete = True
    state.save(workflow.state_file)

    _argv(monkeypatch, "--workspace", str(ws), "--resume", "--step", "2")
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 11


def _forged_workflow(tmp_path, step2_done: bool):
    """Workspace with a state forged past (or before) step 2."""
    from pcappuller.workflow import WorkflowState

    ws = tmp_path / "ws3"
    workflow = ThreeStepWorkflow(ws)
    processed = ws / "processed" / "merged.pcapng"
    if step2_done:
        processed.parent.mkdir(parents=True, exist_ok=True)
        processed.write_bytes(b"x")
    state = WorkflowState(
        workspace_dir=ws,
        root_dirs=[tmp_path],
        window=WINDOW,
        include_patterns=[],
        exclude_patterns=[],
        step1_complete=True,
        step2_complete=step2_done,
        processed_file=processed if step2_done else None,
    )
    state.save(workflow.state_file)
    return workflow, state


def _step3_args(**overrides):
    from argparse import Namespace

    base = dict(snaplen=None, convert_to_pcap=False, gzip=False, out=None, verbose=False)
    base.update(overrides)
    return Namespace(**base)


def test_step3_noop_leaves_step3_pending(tmp_path, capsys):
    """No cleaning flags: step 3 must stay pending so a later --gzip run works."""
    workflow, state = _forged_workflow(tmp_path, step2_done=True)
    result = cli.run_step3(workflow, state, _step3_args())
    assert result.step3_complete is False
    assert result.cleaned_file is None
    assert "skipping" in capsys.readouterr().out


def test_step3_noop_before_step2_raises(tmp_path):
    """--step 3 on a workflow that never ran step 2 must not poison state."""
    workflow, state = _forged_workflow(tmp_path, step2_done=False)
    with pytest.raises(PCAPPullerError, match="Step 2 must be completed"):
        cli.run_step3(workflow, state, _step3_args())


def test_step3_out_refuses_to_clobber_foreign_file(tmp_path, fake_run):
    """--out pointing at an existing unrelated file must not be overwritten."""
    workflow, state = _forged_workflow(tmp_path, step2_done=True)
    foreign = tmp_path / "evidence.pcapng"
    foreign.write_bytes(b"unrelated evidence")
    with pytest.raises(TempSpaceError, match="Refusing to overwrite"):
        cli.run_step3(workflow, state, _step3_args(snaplen=96, out=str(foreign)))
    assert foreign.read_bytes() == b"unrelated evidence"
