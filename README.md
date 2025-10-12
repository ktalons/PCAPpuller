# PCAPpuller

[![GitHub release](https://img.shields.io/github/v/release/ktalons/daPCAPpuller)](https://github.com/ktalons/daPCAPpuller/releases/latest)
[![CI](https://github.com/ktalons/daPCAPpuller/workflows/CI/badge.svg)](https://github.com/ktalons/daPCAPpuller/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A fast PCAP window selector, merger, trimmer, and cleaner.

PCAPpuller helps analysts extract exact time windows from large rolling PCAP/PCAPNG collections and clean captures for downstream analysis. It provides a safe, resumable three-step workflow and prevents “size inflation” caused by duplicate/consolidated files.

- Three-step workflow: Select → Process → Clean (safe to resume)
- Prevents size inflation via smart pattern filtering
- Exact time window extraction and trimming
- GUI and CLI; works with PCAP and PCAPNG; optional gzip compression
- Relies on Wireshark CLI tools (tshark, mergecap, editcap, capinfos)

---

## Install

- GUI (recommended): download from the latest release
  - https://github.com/ktalons/daPCAPpuller/releases/latest
- CLI: Python 3.8+ and Wireshark CLI tools
  - pip install pcappuller[datetime]
  - Installs commands: pcap-puller, pcap-clean, pcap-puller-gui (console launcher)

### Requirements
- Wireshark CLI tools on PATH: tshark, mergecap, editcap, capinfos
- For source installs of the GUI only: PySimpleGUI is hosted on a private index. If needed:
  - python3 -m pip install --extra-index-url https://PySimpleGUI.net/install PySimpleGUI

---

## Quick start

### GUI
1) Launch PCAPpuller GUI (see releases)
2) Set Source directory, Start time, and Duration (or End time)
3) Optional: Pattern Settings, Display filter, Gzip
4) Click Run Workflow (Step 1 and Step 2 enabled by default)

### CLI: Three-step workflow (recommended)
- Complete workflow (solves size inflation):
  - pcap-puller --workspace /tmp/job --source /mnt/dir --start "YYYY-MM-DD HH:MM:SS" --minutes 15 --snaplen 256 --gzip
- Run individual steps for more control:
  - pcap-puller --workspace /tmp/job --step 1 --source /mnt/dir --start "YYYY-MM-DD HH:MM:SS" --minutes 15
  - pcap-puller --workspace /tmp/job --step 2 --resume --display-filter "dns"
  - pcap-puller --workspace /tmp/job --step 3 --resume --snaplen 256 --gzip
- Check status any time:
  - pcap-puller --workspace /tmp/job --status

### Clean an existing capture
- pcap-clean --input big.pcapng --snaplen 256 --filter "tcp or udp or icmp" --split-seconds 300
- Trim and filter a window:
  - pcap-clean --input file.pcap --start "2025-10-02 10:00:00" --end "2025-10-02 10:15:00" --filter "ip.addr==10.0.0.5 && tcp.port==443"

---

## Documentation
- Analyst Guide: docs/Analyst-Guide.md
- Changelog: CHANGELOG.md (see releases for notes)
- License: LICENSE

---

## Development
- Create a venv and install locally:
  - python3 -m pip install -e .[datetime]
  - Optional (GUI from source): python3 -m pip install --extra-index-url https://PySimpleGUI.net/install PySimpleGUI
- Tooling:
  - python3 -m pip install pre-commit ruff mypy
  - pre-commit install && pre-commit run --all-files
- CI runs ruff and mypy (see .github/workflows/ci.yml)

---

## Troubleshooting
- Tools not found: install Wireshark CLI tools and ensure they’re on PATH
- No candidate files: increase --slop-min, verify time window, try without --precise-filter, or run --step 1 --dry-run
- Temp disk full: set --tmpdir to a larger filesystem or reduce --batch-size
