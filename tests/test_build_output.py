"""Unit tests for pcappuller.core.build_output — all external tools faked via RunRecorder."""

from __future__ import annotations

import datetime as dt
import gzip
import shutil
import types
from pathlib import Path

import pytest

import pcappuller.core as core
from pcappuller.core import Window, build_output
from pcappuller.errors import PCAPPullerError, TempSpaceError

WINDOW = Window(start=dt.datetime(2024, 1, 1, 0, 0, 0), end=dt.datetime(2024, 1, 1, 1, 0, 0))


def _candidates(tmp_path: Path, make_minimal_pcap, n: int) -> list[Path]:
    return [make_minimal_pcap(tmp_path / "src" / f"cap_{i:03d}.pcap") for i in range(n)]


def _merge_inputs(argv: list[str]) -> list[str]:
    """Inputs of a mergecap call: everything after `-w OUT`."""
    return argv[argv.index("-w") + 2 :]


def _patch_rlimit(monkeypatch, soft: int = 1 << 20, hard: int = 1 << 20) -> None:
    """Pin core.resource.getrlimit so the NOFILE clamp is deterministic."""
    fake = types.SimpleNamespace(RLIMIT_NOFILE=0, getrlimit=lambda _res: (soft, hard))
    monkeypatch.setattr(core, "resource", fake)


def _build(candidates, out_path: Path, **kw) -> Path:
    defaults = dict(
        window=WINDOW,
        tmpdir_parent=None,
        batch_size=100,
        out_format="pcapng",
        display_filter=None,
        gzip_out=False,
    )
    defaults.update(kw)
    return build_output(candidates, out_path=out_path, **defaults)


def test_empty_candidates_raises(tmp_path):
    """No candidates is a controlled PCAPPullerError, before any tool runs."""
    with pytest.raises(PCAPPullerError, match="No target PCAP files found"):
        _build([], tmp_path / "out.pcapng")


def test_batching_math(tmp_path, make_minimal_pcap, fake_run, monkeypatch):
    """7 inputs at batch_size=3 -> ceil(7/3)=3 batch merges (<=3 inputs each) + 1 final merge."""
    _patch_rlimit(monkeypatch)
    cands = _candidates(tmp_path, make_minimal_pcap, 7)
    out = _build(cands, tmp_path / "out.pcapng", batch_size=3)
    assert out == tmp_path / "out.pcapng"

    merges = fake_run.argv_for("mergecap")
    assert len(merges) == 4  # 3 batches + final combine
    batch_inputs = [_merge_inputs(a) for a in merges[:3]]
    assert [len(b) for b in batch_inputs] == [3, 3, 1]
    flat = [p for b in batch_inputs for p in b]
    assert flat == [str(p) for p in sorted(cands)]
    # Final merge consumes the batch intermediates, not the original candidates
    assert all("batch_" in Path(p).name for p in _merge_inputs(merges[3]))


def test_rlimit_nofile_clamps_batch_size(tmp_path, make_minimal_pcap, fake_run, monkeypatch):
    """soft limit 64 clamps the effective batch to 32 even when batch_size=500."""
    _patch_rlimit(monkeypatch, soft=64, hard=1024)
    cands = _candidates(tmp_path, make_minimal_pcap, 40)
    _build(cands, tmp_path / "out.pcapng", batch_size=500)

    merges = fake_run.argv_for("mergecap")
    assert len(merges) == 3  # ceil(40/32)=2 batches + final combine
    sizes = [len(_merge_inputs(a)) for a in merges[:2]]
    assert sizes == [32, 8]
    assert all(s <= 32 for s in sizes)


def test_trim_per_batch_multi_batch(tmp_path, make_minimal_pcap, fake_run, monkeypatch):
    """trim_per_batch: one editcap per batch, final merge of trimmed batches, no global trim."""
    _patch_rlimit(monkeypatch)
    cands = _candidates(tmp_path, make_minimal_pcap, 5)
    _build(cands, tmp_path / "out.pcapng", batch_size=2, trim_per_batch=True)

    edits = fake_run.argv_for("editcap")
    assert len(edits) == 3  # ceil(5/2) batches, one trim each — no extra global trim
    for argv in edits:
        assert "_trimmed." in Path(argv[-1]).name  # dst is the per-batch trimmed file
        assert Path(argv[-2]).name.startswith("batch_")  # src is that batch's merge output

    merges = fake_run.argv_for("mergecap")
    assert len(merges) == 4  # 3 batch merges + final merge of trimmed outputs
    final_inputs = _merge_inputs(merges[-1])
    assert len(final_inputs) == 3
    assert all("_trimmed." in Path(p).name for p in final_inputs)
    # The final merge runs after every per-batch trim
    assert fake_run.calls.index(merges[-1]) > max(fake_run.calls.index(e) for e in edits)


def test_trim_per_batch_single_batch(tmp_path, make_minimal_pcap, fake_run, monkeypatch):
    """trim_per_batch with one batch: merge + trim only, no recombine merge."""
    _patch_rlimit(monkeypatch)
    cands = _candidates(tmp_path, make_minimal_pcap, 3)
    out = _build(cands, tmp_path / "out.pcapng", batch_size=10, trim_per_batch=True)

    assert len(fake_run.argv_for("mergecap")) == 1
    assert len(fake_run.argv_for("editcap")) == 1
    assert out.read_bytes() == b"FAKEeditcap"


def test_global_trim_single_editcap(tmp_path, make_minimal_pcap, fake_run, monkeypatch):
    """trim_per_batch=False: batches merge to one file, then exactly one global editcap trim."""
    _patch_rlimit(monkeypatch)
    cands = _candidates(tmp_path, make_minimal_pcap, 5)
    _build(cands, tmp_path / "out.pcapng", batch_size=2)

    edits = fake_run.argv_for("editcap")
    assert len(edits) == 1
    argv = edits[0]
    assert Path(argv[-2]).name == "merged_all.pcapng"
    assert Path(argv[-1]).name == "trimmed.pcapng"
    assert argv[argv.index("-A") + 1] == "2024-01-01 00:00:00"
    assert argv[argv.index("-B") + 1] == "2024-01-01 01:00:00"


def test_display_filter_runs_tshark(tmp_path, make_minimal_pcap, fake_run, monkeypatch):
    """A display filter routes the trimmed file through tshark -Y; its output is the result."""
    _patch_rlimit(monkeypatch)
    cands = _candidates(tmp_path, make_minimal_pcap, 2)
    out = _build(cands, tmp_path / "out.pcapng", display_filter="tcp.port == 443")

    shark = fake_run.argv_for("tshark")
    assert len(shark) == 1
    argv = shark[0]
    assert argv[argv.index("-Y") + 1] == "tcp.port == 443"
    assert Path(argv[argv.index("-r") + 1]).name == "trimmed.pcapng"
    assert Path(argv[argv.index("-w") + 1]).name == "final.pcapng"
    assert out.read_bytes() == b"FAKEtshark"  # final file is tshark's output, not editcap's


def test_gzip_appends_suffix_and_is_valid_gzip(tmp_path, make_minimal_pcap, fake_run, monkeypatch):
    """gzip_out=True appends .gz to out_path and writes a real gzip stream of the fake bytes."""
    _patch_rlimit(monkeypatch)
    cands = _candidates(tmp_path, make_minimal_pcap, 2)
    out_path = tmp_path / "result" / "capture.pcap"
    result = _build(cands, out_path, out_format="pcap", gzip_out=True)

    assert result == out_path.with_suffix(".pcap.gz")
    assert result.exists()
    with gzip.open(result, "rb") as fh:
        assert fh.read() == b"FAKEeditcap"


def test_plain_output_moved_to_out_path(tmp_path, make_minimal_pcap, fake_run, monkeypatch):
    """No filter, no gzip: the trimmed file is moved to out_path and out_path is returned."""
    _patch_rlimit(monkeypatch)
    cands = _candidates(tmp_path, make_minimal_pcap, 2)
    out_path = tmp_path / "deep" / "nested" / "out.pcapng"
    result = _build(cands, out_path)

    assert result == out_path
    assert out_path.exists()
    assert out_path.read_bytes() == b"FAKEeditcap"


def test_oserror_maps_to_tempspace_with_tmpdir_hint(
    tmp_path, make_minimal_pcap, fake_run, monkeypatch
):
    """OSError during the final move becomes TempSpaceError; hint shown when tmpdir_parent=None."""
    _patch_rlimit(monkeypatch)
    assert issubclass(TempSpaceError, PCAPPullerError)
    cands = _candidates(tmp_path, make_minimal_pcap, 2)

    def _boom(src, dst):
        raise OSError("no space left on device")

    monkeypatch.setattr(shutil, "move", _boom)
    with pytest.raises(TempSpaceError, match=r"--tmpdir"):
        _build(cands, tmp_path / "out.pcapng", tmpdir_parent=None)


def test_oserror_no_hint_when_tmpdir_parent_given(
    tmp_path, make_minimal_pcap, fake_run, monkeypatch
):
    """With an explicit tmpdir_parent the --tmpdir hint is suppressed."""
    _patch_rlimit(monkeypatch)
    cands = _candidates(tmp_path, make_minimal_pcap, 2)
    parent = tmp_path / "tmpparent"
    parent.mkdir()

    def _boom(src, dst):
        raise OSError("no space left on device")

    monkeypatch.setattr(shutil, "move", _boom)
    with pytest.raises(TempSpaceError) as exc:
        _build(cands, tmp_path / "out.pcapng", tmpdir_parent=parent)
    assert "--tmpdir" not in str(exc.value)
