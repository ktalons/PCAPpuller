# PCAPpuller

[![CI](https://github.com/ktalons/PCAPpuller/actions/workflows/ci.yml/badge.svg)](https://github.com/ktalons/PCAPpuller/actions/workflows/ci.yml)
[![GitHub release](https://img.shields.io/github/v/release/ktalons/PCAPpuller)](https://github.com/ktalons/PCAPpuller/releases/latest)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Pull an exact time window out of a large rolling PCAP collection, merge it into one
capture, and clean it for analysis. Built for SOC work where the evidence you need
is 15 minutes spread across thousands of rotating capture files.

**Project page:** <https://ktalons.github.io/projects/pcappuller/>

## What it does

Three resumable steps, each checkpointed in a workspace directory:

| Step | Name | What happens |
|------|------|--------------|
| 1 | Select | Find candidate files by mtime window + name patterns (no data copied) |
| 2 | Process | Precise-filter by packet times, merge in batches, trim to the exact window |
| 3 | Clean | Optional: truncate payloads, convert to pcap, gzip |

Batch merging plus per-batch trimming keeps temp-space bounded on long windows,
and the capinfos results are cached so re-runs over the same files are fast.

## Install

| Method | Command |
|--------|---------|
| CLI via pipx | `pipx install "git+https://github.com/ktalons/PCAPpuller"` |
| CLI via Homebrew | `brew install ktalons/tap/pcappuller` |
| GUI app (macOS) | `brew install --cask ktalons/tap/pcappuller` |
| GUI binaries | [latest release](https://github.com/ktalons/PCAPpuller/releases/latest) (macOS, Linux, Windows) |

Requires the Wireshark CLI tools on PATH: `mergecap`, `editcap`, `capinfos`, and
`tshark` for display filters (`brew install wireshark` / `sudo apt install tshark`).
Python 3.10+.

## Usage

```bash
# Full workflow: select, process, and write the merged window to a file
pcap-puller --workspace /tmp/job --source /mnt/captures \
  --start "2026-01-15 10:00:00" --minutes 15 --out /cases/incident.pcapng

# Or run steps individually and resume between them
pcap-puller --workspace /tmp/job --step 1 --source /mnt/captures --start "2026-01-15 10:00:00" --minutes 15
pcap-puller --workspace /tmp/job --step 2 --resume --display-filter "dns"
pcap-puller --workspace /tmp/job --step 3 --resume --snaplen 256 --gzip
pcap-puller --workspace /tmp/job --status
```

`pcap-clean` post-processes a single existing capture (reorder, trim, snaplen,
filter, split). `pcap-puller-gui` opens the GUI. Full walkthrough:
[docs/Analyst-Guide.md](docs/Analyst-Guide.md).

## Status and scope

In dev; functional today. The unit suite and an end-to-end CI smoke test cover the
engine, and v0.4.0 consolidated the codebase to one canonical implementation.

- [x] Three-step CLI workflow with resume and status
- [x] GUI (FreeSimpleGUI) with the same engine
- [x] Unit tests + CI matrix (Linux/macOS, Python 3.10-3.13)
- [ ] GUI cancel cannot yet kill an in-flight merge (takes effect between phases)
- [ ] No packet rewriting or anonymization -- out of scope for now

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,datetime]"
pytest -q          # unit tests (no Wireshark tools needed)
ruff check . && mypy pcappuller
pre-commit install
```
