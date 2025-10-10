# PCAPpuller 👊

[![GitHub release](https://img.shields.io/github/v/release/ktalons/daPCAPpuller)](https://github.com/ktalons/daPCAPpuller/releases/latest)
[![CI](https://github.com/ktalons/daPCAPpuller/workflows/CI/badge.svg)](https://github.com/ktalons/daPCAPpuller/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## A fast PCAP window selector, merger, trimmer, and cleaner ⏩

PCAPpuller is a comprehensive network analysis tool that helps you extract, clean, and analyze packets from large PCAP collections with enterprise-grade filtering capabilities.

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

## What's New in v0.2.3 ✨
- **🔍 Massive Filter Expansion**: 300+ Wireshark display filters across 41 protocol categories
- **🎨 GUI Clean Integration**: Complete PCAP cleaning functionality in the GUI interface
- **📱 Desktop Integration**: Proper icons and desktop files for Linux packages  
- **🔧 Enhanced CI/CD**: Improved testing and build processes
- **🎯 Professional Analysis**: Enterprise-grade filtering matching Wireshark's capabilities

## Core Features 🧰
- **🗂 PCAP Window Extraction**: Pull exact time windows from large rolling collections
- **🧽 PCAP Cleaning**: Convert, reorder, truncate, filter, and split captures
- **2️⃣ Two-Phase Selection**: Fast mtime prefilter + optional precise capinfos filtering
- **⚡ Parallel Processing**: Multi-threaded capinfos analysis for thousands of files
- **🧩 Smart Batching**: Efficient mergecap operations to avoid memory issues
- **✂️ Precise Trimming**: Exact time boundaries with editcap
- **🔍 Advanced Filtering**: 300+ Wireshark display filters for comprehensive analysis
- **🏁 Format Control**: Output as pcap/pcapng with optional gzip compression
- **🧪 Audit Mode**: Dry-run with detailed reporting and survivor lists
- **🎨 GUI Interface**: User-friendly desktop application with progress tracking
___
## How it works ⚙️
1. Scan --root for *.pcap, *.pcapng, *.cap whose mtime falls within [start-slop, end+slop].
2. (Optional) Refine with capinfos -a -e -S in parallel to keep only files that truly overlap the window.
3. Merge candidates in batches with mergecap (limits memory and argv size).
4. Trim the merged file to [start, end] with editcap -A/-B.
5. (Optional) Filter with tshark -Y "<display filter>".
6. Write as pcap/pcapng, optionally gzip.
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
### Installed (via console scripts)
- `pcap-puller --root /mnt/dir --start "YYYY-MM-DD HH:MM:SS" --minutes 15 --out out.pcapng`
- `pcap-puller --root /mnt/dir1 /mnt/dir2 --start "YYYY-MM-DD HH:MM:SS" --end "YYYY-MM-DD HH:MM:SS" --out out.pcapng`
- `pcap-puller --root /mnt/dir --start "YYYY-MM-DD HH:MM:SS" --minutes 15 --precise-filter --workers auto --display-filter "dns" --gzip --verbose`
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
`python3 PCAPpuller.py --root /mnt/your-rootdir --start "YYYY-MM-DD HH:MM:SS" --minutes <1-60> --out /path/to/output.pcapng`
`python3 PCAPpuller.py --root /mnt/dir1 /mnt/dir2 --start "YYYY-MM-DD HH:MM:SS" --end "YYYY-MM-DD HH:MM:SS" --out /path/to/output.pcapng`
`python3 PCAPpuller.py --root /mnt/your-rootdir --start "YYYY-MM-DD HH:MM:SS" --minutes <1-60> --out /path/to/output_dns.pcap.gz --out-format pcap --tmpdir /big/volume/tmp --batch-size 500 --slop-min 120 --precise-filter --workers auto --display-filter "dns" --gzip --verbose`
`python3 PCAPpuller.py --root /mnt/your-rootdir --start "YYYY-MM-DD HH:MM:SS" --minutes <1-60> --precise-filter --workers auto --dry-run --list-out /path/to/list.csv --summary`
___
## Arguments 💥
### Required ❗
> `--root </root/directory ...>` — one or more directories to search.<br>
> `--start "YYYY-MM-DD HH:MM:SS"` — window start (local time).<br>
> `--minutes <1–60>` — duration; must stay within a single calendar day. Or use `--end` with same-day end time.<br>
> `--out </output/path>` — output file (not required if you use --dry-run).<br>
### Optional ❓
> `--end <YYYY-MM-DD HH:MM:SS>` — end time instead of `--minutes` (must be same day as `--start`).<br>
> `--tmpdir </temp/path>` — where to write temporary/intermediate files. **Highly recommended** on a large volume (e.g., the NAS).<br>
> `--batch-size <INT>` — files per merge batch (default: 500).<br>
> `--slop-min <INT>` — mtime prefilter slack minutes (default: 120).<br>
> `--precise-filter` — use capinfos first/last packet times to keep only overlapping files.<br>
> `--workers <auto|INT>` — concurrency for precise filter (default: auto ≈ 2×CPU, gently capped).<br>
> `--display-filter "<Wireshark filter>"` — post-trim filter via tshark (e.g., "dns", "tcp.port==443").<br>
> `--out-format {pcap|pcapng}` — final capture format (default: pcapng).<br>
> `--gzip` — gzip-compress the final output (writes .gz).<br>
> `--dry-run` — selection only; no merge/trim/write.<br>
> `--list-out <FILE.{txt|csv}>` — with `--dry-run`, write survivor list to file.<br>
> `--report <FILE.csv>` — write a CSV report for survivors with path,size,mtime,first,last (uses cache/capinfos).<br>
> `--summary` — with `--dry-run`, print min/max packet times across survivors (UTC).
> `--verbose` — print debug logs and show external tool output.
___
## Tips 🗯️ 
- Use --tmpdir on a large volume (e.g., the NAS) if your /tmp is small.
- --precise-filter reduces I/O by skipping irrelevant files; tune --workers to match NAS throughput.
- Metadata caching speeds up repeated runs. Default cache location:
  - macOS/Linux: ~/.cache/pcappuller/capinfos.sqlite (respects XDG_CACHE_HOME)
  - Windows: %LOCALAPPDATA%\pcappuller\capinfos.sqlite
  - Control with `--cache <PATH>`, disable with `--no-cache`, clear with `--clear-cache`.
- Display filters use Wireshark display syntax (not capture filters).
- For auditing, run --dry-run --list-out list.csv first; add `--summary` to see min/max packet times.
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
