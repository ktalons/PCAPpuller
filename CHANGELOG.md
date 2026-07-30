# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project adheres to Semantic Versioning.

## [v0.4.0] - 2026-07-30

Stability and consolidation release: one canonical implementation, a real test
suite, and fixes for every known silent-data bug.

### Breaking

- `pcap-puller` is now the three-step workflow CLI (`--workspace/--step/--source`),
  matching what the docs have described since v0.3.0. The legacy one-shot CLI
  (`--root/--out`) and legacy GUI are removed.
- Step 3 with no cleaning flags is now a no-op. It previously converted to pcap
  and gzipped implicitly, changing the output format without being asked.
- `pcap-clean --snaplen` defaults to 0 (disabled). It previously truncated
  payloads to 256 bytes by default.
- The GUI dependency is now FreeSimpleGUI (installable from PyPI). PySimpleGUI
  still works as a fallback if already installed.
- Python 3.10+ required (was 3.8, which is EOL).

### Fixed

- Installed `pcap-puller` entry point pointed at the legacy CLI, so every
  documented three-step command failed on a pip install.
- Missing Wireshark tools are now caught up front with a clear message; a missing
  `mergecap` previously surfaced as a misleading temp-space error, and a missing
  `capinfos` silently dropped every file during precise filtering.
- `--trim-per-batch` auto-detection was unreachable; long windows (>60 min) now
  get per-batch trimming again, as v0.3.0 intended.
- Step 3 snaplen output was pcapng mislabeled with a `.pcap` name (editcap's
  default format was used); the format now always matches the extension.
- `--out` was ignored when Step 3 ran; the final cleaned artifact now lands at
  the requested path with its real extension chain.
- Workflow state writes are atomic and versioned; a crash mid-write can no
  longer corrupt `--resume`, and `--resume` now derives auto-settings from the
  saved window instead of a 60-minute fallback.
- GUI: per-run temp workspaces are cleaned up (multi-GB leak), Step 2/3-only
  runs work against an existing workspace, the recommendation label renders on
  startup, and worker logging is thread-safe.
- Merge batches are clamped to the process open-files limit (macOS defaults to
  256, below the old batch sizes).
- External tool failures now include the tool's stderr instead of a bare exit
  status; `capinfos` calls time out after 60s instead of hanging on dead mounts.
- Windows: CLI output is ASCII-only (emoji crashed cp1252 consoles).

### Added

- `--version` on `pcap-puller` and `pcap-clean`; single version source in
  `pcappuller.__version__`.
- Unit test suite and CI matrix (Linux + macOS, Python 3.10-3.13) with an
  end-to-end smoke test under real Wireshark tools.
- Typed error hierarchy with stable exit codes (3 time, 10 disk, 11 tools).
- capinfos cache: batched commits, integer mtimes, 30-day pruning.

### Removed

- ~1,800 lines of duplicated/dead code: `PCAPpuller.py`, `PCAPpuller_legacy.py`,
  `gui_pcappuller_legacy.py`, `pcappuller/gui_v2.py`, stale `packaging/homebrew/`
  seed, placeholder demo media. `gui_pcappuller.py` is now a thin PyInstaller shim.

## [v0.3.1] - 2025-10-12

### Added

- `--source` as the preferred selection flag (`--root` kept as hidden alias)
- Selection modes: manifest (default, no data copied) and symlink
- Precise filtering moved from Step 1 to Step 2 (on by default there)
- `--out` and `--tmpdir` pass-through for Step 2; GUI verbose logging

### Changed

- Default include patterns simplified to `*.pcap`, `*.pcapng` with no default
  excludes (was `*.chunk_*.pcap` include with sorted/s256 excludes)

## [v0.3.0] - 2025-10-10

### Highlights
- NEW three-step workflow (Select → Process → Clean) with workspace management
- Smart pattern filtering that eliminates 3× file size inflation
- Updated GUI with Pattern Settings, advanced controls, and step-by-step progress

### Added
- ThreeStepWorkflow with workspace structure: selected/, processed/, cleaned/, tmp/
- CLI: `--workspace`, `--step {1,2,3,all}`, `--resume`, `--status`, pattern
  controls, processing controls, cleaning options
- GUI: three-step controls, Pattern Settings dialog, Advanced Settings,
  step indicator and progress callbacks

### Changed
- Default UX is the new three-step workflow; legacy one-shot flow preserved separately
- Improved temporary directory handling

### Fixed
- Eliminates file size inflation caused by processing both chunk files and consolidated files simultaneously
- Ensures stable operation across large windows with batch trimming and status/resume

## [v0.2.3] - 2025-10-10

### Highlights
- Massive Wireshark filter expansion (300+ filters across 41 protocol categories)
- GUI "Clean" integration with convert/reorder/snaplen/filter/split
- Desktop integration (icons, desktop files for Linux packages)
- Enhanced CI/CD and testing
