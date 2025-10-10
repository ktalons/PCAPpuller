# PCAPpuller 👊

[![GitHub release](https://img.shields.io/github/v/release/ktalons/daPCAPpuller)](https://github.com/ktalons/daPCAPpuller/releases/latest)
[![CI](https://github.com/ktalons/daPCAPpuller/workflows/CI/badge.svg)](https://github.com/ktalons/daPCAPpuller/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## A fast PCAP window selector, merger, trimmer, and cleaner ⏩

PCAPpuller is a comprehensive network analysis tool with a **three-step workflow** that helps you extract, clean, and analyze packets from large PCAP collections with enterprise-grade filtering capabilities.

**🔧 NEW: Solves file size inflation issues** with smart pattern filtering that prevents duplicate data processing.

---

## Install the GUI (recommended) 🖥️
The easiest way to use PCAPpuller is the desktop GUI. Download it from the latest release:
- https://github.com/ktalons/daPCAPpuller/releases/latest

Requirements for the GUI binary: Wireshark CLI tools (tshark, mergecap, editcap, capinfos) installed on your system PATH. See Install Wireshark CLI tools below if needed.

- macOS
  - If you downloaded a .app bundle (recommended):
    1) Download PCAPpullerGUI-macos.zip and extract PCAPpullerGUI.app
    2) Optional: move PCAPpullerGUI.app to /Applications
    3) First run: right-click → Open (or: xattr -dr com.apple.quarantine "/Applications/PCAPpullerGUI.app" or "/path/to/PCAPpullerGUI.app")
  - If you downloaded a single-file binary (no .app):
    1) Download PCAPpullerGUI-macos
    2) In Terminal:
       - chmod +x "/path/to/PCAPpullerGUI-macos"
       - xattr -d com.apple.quarantine "/path/to/PCAPpullerGUI-macos"  # if needed
    3) Run it from Terminal to avoid TextEdit opening it as a text file:
       - ./PCAPpullerGUI-macos
       - or: open -a Terminal "/path/to/PCAPpullerGUI-macos"

- Windows
  1) Download PCAPpullerGUI-windows.exe from the latest release
  2) If SmartScreen warns, click “More info” → “Run anyway”

- Linux
  - Portable binary
    1) Download PCAPpullerGUI-linux
    2) chmod +x ./PCAPpullerGUI-linux && ./PCAPpullerGUI-linux
  - Packages
    - Debian/Ubuntu: sudo dpkg -i pcappuller-gui_*.deb && sudo apt -f install
    - Fedora/RHEL: sudo rpm -Uvh pcappuller-gui-*.rpm

### Run the GUI
- macOS: 
  - If you have PCAPpullerGUI.app: double-click it (or right-click → Open on first run)
  - If you have a single-file binary: run from Terminal: ./PCAPpullerGUI-macos (use chmod +x first if needed)
- Linux: run from Terminal: ./PCAPpullerGUI-linux (use chmod +x first)
- Windows: double-click PCAPpullerGUI-windows.exe

### Quickstart (GUI)
**PCAP Window Extraction:**
1. Pick Root folder(s) containing your PCAP/PCAPNG files
2. Set Start time and Duration (Hours/Minutes)
3. Optional: Precise filter, Display filter (300+ filters available), Gzip
4. Choose output file path
5. Click Run — progress will appear; cancel anytime

**PCAP Cleaning:**
1. Click "Clean..." button
2. Select input PCAP/PCAPNG file
3. Configure options: format conversion, reordering, snaplen, filtering
4. Optional: time window trimming, output splitting
5. Click "Clean" — creates optimized capture files

---

## What's New in v0.3.0 ✨
- **🔧 SIZE INFLATION FIX**: Solves 3x file size inflation with smart pattern filtering
- **📋 Three-Step Workflow**: Select → Process → Clean for better control and efficiency
- **🎯 Smart File Filtering**: Automatically excludes duplicate/consolidated files
- **💾 Workspace Management**: Organized temporary file handling with resumable operations
- **🔄 Enhanced GUI**: Pattern settings, step-by-step progress, advanced controls
- **📏 Documentation**: Complete workflow guide and migration assistance

## Core Features 🧰
- **📋 Three-Step Workflow**: Select → Process → Clean with resumable operations
- **🔧 Size Inflation Fix**: Smart pattern filtering prevents duplicate data processing  
- **🗂 PCAP Window Extraction**: Pull exact time windows from large rolling collections
- **🧵 PCAP Cleaning**: Convert, reorder, truncate, filter, and split captures
- **🎯 Pattern Filtering**: Automatically exclude consolidated/backup files
- **⚡ Parallel Processing**: Multi-threaded capinfos analysis for thousands of files
- **🧩 Smart Batching**: Efficient mergecap operations to avoid memory issues
- **✂️ Precise Trimming**: Exact time boundaries with editcap
- **🔍 Advanced Filtering**: 300+ Wireshark display filters for comprehensive analysis
- **🏁 Format Control**: Output as pcap/pcapng with optional gzip compression
- **🧪 Audit Mode**: Dry-run with detailed reporting and survivor lists
- **🎨 GUI Interface**: Enhanced desktop application with step-by-step progress
___
## How it works ⚙️

### Three-Step Workflow:
**Step 1: Select & Filter**
1. Scan --root directories for PCAP files
2. Apply include/exclude patterns (e.g., include `*.chunk_*.pcap`, exclude `*.sorted.pcap`)
3. Filter by mtime within [start-slop, end+slop]
4. (Optional) Precise filtering with capinfos to verify packet times
5. Copy selected files to organized workspace

**Step 2: Process** 
6. Merge selected files in efficient batches with mergecap
7. Trim merged file to exact [start, end] window with editcap
8. (Optional) Apply display filters with tshark

**Step 3: Clean (Optional)**
9. Truncate packets (snaplen) to save space
10. Convert formats (pcapng → pcap)
11. Compress with gzip
___
## Prerequisites ☑️
- For the GUI binary: Wireshark CLI tools available on PATH (tshark, mergecap, editcap, capinfos). No Python required.
- For the CLI (pip install): Python 3.8+ and Wireshark CLI tools.
- **Note**: PySimpleGUI has moved to a private PyPI server. To install from source, use: `python3 -m pip install --extra-index-url https://PySimpleGUI.net/install PySimpleGUI`

### Install Wireshark CLI tools
> Debian/Ubuntu
> sudo apt-get update
> sudo apt-get install wireshark
#
> Manjaro/Arch
> sudo pacman -Syu wireshark
# 
> Fedora/CentOS/RHEL
> sudo dnf install wireshark
#
> macOS (Homebrew)
> brew install wireshark
#
> Windows (PowerShell, Admin)
> winget install WiresharkFoundation.Wireshark
> 
> If Wireshark CLI tools aren’t in PATH, the app will also look in common install dirs.
___
## Quick Usage ⭐

### Three-Step Workflow (Recommended)
```bash
# Complete workflow - solves size inflation issues!
pcap-puller --workspace /tmp/job --root /mnt/dir --start "YYYY-MM-DD HH:MM:SS" --minutes 15 --snaplen 256 --gzip

# Individual steps for more control
pcap-puller --workspace /tmp/job --step 1 --root /mnt/dir --start "YYYY-MM-DD HH:MM:SS" --minutes 15  # Select
pcap-puller --workspace /tmp/job --step 2 --resume --display-filter "dns"  # Process  
pcap-puller --workspace /tmp/job --step 3 --resume --snaplen 256 --gzip  # Clean

# Check status anytime
pcap-puller --workspace /tmp/job --status
```

### Legacy Mode (console scripts)
- `pcap-puller --root /mnt/dir --start "YYYY-MM-DD HH:MM:SS" --minutes 15 --out out.pcapng`
- `pcap-puller --root /mnt/dir1 /mnt/dir2 --start "YYYY-MM-DD HH:MM:SS" --end "YYYY-MM-DD HH:MM:SS" --out out.pcapng`
- Dry-run: `pcap-puller --root /mnt/dir --start "YYYY-MM-DD HH:MM:SS" --minutes 15 --dry-run --list-out list.csv --summary --report survivors.csv`

### Clean a large/processed capture
**GUI**: Click "Clean..." button for intuitive interface with all options

**CLI Examples:**
- Convert to classic pcap, reorder, truncate, filter, and split:
  - `pcap-clean --input /path/to/big.pcapng --snaplen 256 --filter "tcp || udp || icmp || icmpv6" --split-seconds 60`
- Keep original format and just reorder + snaplen:
  - `pcap-clean --input /path/to/big.pcapng --keep-format --snaplen 128`
- Trim to time window and filter to specific host/port:
  - `pcap-clean --input /path/file.pcap --start "2025-10-02 10:00:00" --end "2025-10-02 10:15:00" --filter "ip.addr==10.0.0.5 && tcp.port==443"`
- Custom output directory:
  - `pcap-clean --input /path/file.pcapng --out-dir /tmp/cleaned/ --snaplen 256`

### Direct (without install)
```bash
# New three-step workflow (recommended)
python3 PCAPpuller.py --workspace /tmp/job --root /mnt/dir --start "YYYY-MM-DD HH:MM:SS" --minutes 30 --snaplen 256 --gzip

# Individual steps
python3 PCAPpuller.py --workspace /tmp/job --step 1 --root /mnt/dir --start "YYYY-MM-DD HH:MM:SS" --minutes 30
python3 PCAPpuller.py --workspace /tmp/job --step 2 --resume --display-filter "dns" 
python3 PCAPpuller.py --workspace /tmp/job --step 3 --resume --snaplen 256 --gzip

# Legacy mode (may cause size inflation)
python3 PCAPpuller_legacy.py --root /mnt/dir --start "YYYY-MM-DD HH:MM:SS" --minutes 30 --out output.pcapng
```
___
## Arguments 💥
### Required ❗
> `--workspace </workspace/path>` — workspace directory for three-step workflow (NEW).<br>
> `--root </root/directory ...>` — one or more directories to search.<br>
> `--start "YYYY-MM-DD HH:MM:SS"` — window start (local time).<br>
> `--minutes <1–1440>` — duration; must stay within a single calendar day. Or use `--end` with same-day end time.<br>
### Optional ❓

**Workflow Control:**
> `--step {1,2,3,all}` — which step to run (default: all).<br>
> `--resume` — resume from existing workflow state.<br>
> `--status` — show workflow status and exit.<br>

**Pattern Filtering (Step 1):**
> `--include-pattern [PATTERNS...]` — include files matching patterns (default: *.chunk_*.pcap).<br>
> `--exclude-pattern [PATTERNS...]` — exclude files matching patterns (default: *.sorted.pcap, *.s256.pcap).<br>

**Processing Options:**
> `--end <YYYY-MM-DD HH:MM:SS>` — end time instead of `--minutes` (must be same day as `--start`).<br>
> `--batch-size <INT>` — files per merge batch (default: 500).<br>
> `--slop-min <INT>` — mtime prefilter slack minutes (default: 120).<br>
> `--precise-filter` — use capinfos first/last packet times to keep only overlapping files.<br>
> `--workers <auto|INT>` — concurrency for precise filter (default: auto ≈ 2×CPU, gently capped).<br>
> `--display-filter "<Wireshark filter>"` — post-trim filter via tshark (e.g., "dns", "tcp.port==443").<br>
> `--out-format {pcap|pcapng}` — final capture format (default: pcapng).<br>

**Cleaning Options (Step 3):**
> `--snaplen <INT>` — truncate packets to N bytes.<br>
> `--convert-to-pcap` — force conversion to pcap format.<br>
> `--gzip` — gzip-compress the final output.<br>

**Other:**
> `--dry-run` — selection only; no merge/trim/write.<br>
> `--verbose` — print debug logs and show external tool output.<br>
___
## Tips 🗿

**Size Inflation Fix:**
- **NEW**: Use `--workspace` to avoid 3x file size inflation issues
- Pattern filtering automatically excludes large consolidated files
- Dry-run first: `--step 1 --dry-run` to verify file selection

**Performance:**
- `--precise-filter` reduces I/O by skipping irrelevant files; tune `--workers` to match NAS throughput
- Individual steps: Run `--step 1`, then `--step 2`, then `--step 3` for better control
- Resume operations: Use `--resume` to continue from failed steps

**Storage & Caching:**
- Workspace management: Files organized in `workspace/{selected,processed,cleaned}` directories  
- Metadata caching speeds up repeated runs. Default cache location:
  - macOS/Linux: ~/.cache/pcappuller/capinfos.sqlite (respects XDG_CACHE_HOME)
  - Windows: %LOCALAPPDATA%\pcappuller\capinfos.sqlite
  - Control with `--cache <PATH>`, disable with `--no-cache`, clear with `--clear-cache`

**Workflow:**
- Display filters use Wireshark display syntax (not capture filters)
- Cleaning options in Step 3 can reduce final file size by 60-90%
- Check status anytime: `--workspace /path --status`
___
## Development 🛠️
- Install tooling (in a virtualenv):
  - python3 -m pip install -e .[datetime]
  - python3 -m pip install --extra-index-url https://PySimpleGUI.net/install PySimpleGUI
  - python3 -m pip install pre-commit ruff mypy
- Enable pre-commit hooks:
  - pre-commit install
  - pre-commit run --all-files
- CI runs ruff (E,F) and mypy on pushes/PRs (see .github/workflows/ci.yml).

## Troubleshooting 🚨
- Temp disk fills up
> Set --tmpdir to a bigger filesystem. Batch size can be reduced via --batch-size.
- “No candidate PCAP files found”
> Try a larger --slop-min, confirm the time window, or test without --precise-filter. Use --dry-run for quick iteration.
- Tools not found
> Ensure Wireshark CLI tools are installed and in PATH. On Windows, common install dirs are auto-checked.
- Permissions with tshark/dumpcap
> On Linux, add your user to the wireshark group and re-login.
___
