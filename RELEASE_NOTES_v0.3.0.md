# PCAPpuller v0.3.0 Release Notes

This release introduces a new three-step workflow that solves file size inflation issues and greatly improves analyst workflow in both the CLI and GUI.

## 🚀 Highlights
- NEW Three-Step Workflow: Select → Process → Clean (with workspace management)
- Size Inflation Fix: Smart pattern filtering prevents 3× output growth
- GUI Improvements: Pattern Settings, Advanced Settings, step-by-step progress
- Resume & Status: Continue from any step, check progress at any time
- Cleaning Options: Snaplen truncation, gzip compression, optional pcap conversion

## 🔧 Why Upgrade
- Prevents accidental inclusion of large consolidated PCAPs alongside chunk files
- Produces minimal-size outputs with optional cleaning (60–90% reduction typical)
- More predictable, resumable, and controllable processing

## 🖥️ GUI Changes
- New workflow checkboxes for Step 1/2/3
- "Pattern Settings" to control include/exclude filename patterns
  - Defaults: include `*.chunk_*.pcap`, exclude `*.sorted.pcap`, `*.s256.pcap`
- Advanced Settings: workers, slop, batch size, trim-per-batch
- Progress display per phase, with current step indicator

## 🧰 CLI (PCAPpuller.py)
- New flags: `--workspace`, `--step {1,2,3,all}`, `--resume`, `--status`
- Pattern filtering: `--include-pattern`, `--exclude-pattern`
- Processing: `--batch-size`, `--out-format`, `--display-filter`, `--trim-per-batch`
- Cleaning: `--snaplen`, `--convert-to-pcap`, `--gzip`

Examples:
```bash
# Complete workflow (recommended)
pcap-puller --workspace /tmp/job --root /data --start "2025-08-26 16:00:00" --minutes 30 --snaplen 256 --gzip

# Individual steps
pcap-puller --workspace /tmp/job --step 1 --root /data --start "2025-08-26 16:00:00" --minutes 30
pcap-puller --workspace /tmp/job --step 2 --resume --display-filter "dns"
pcap-puller --workspace /tmp/job --step 3 --resume --snaplen 256 --gzip
```

## 📦 Downloads
Attach GUI binaries to this release:
- Windows: PCAPpullerGUI-windows.exe
- macOS: PCAPpullerGUI-macos.zip (PCAPpullerGUI.app)
- Linux: PCAPpullerGUI-linux (and/or .deb/.rpm packages)

## 📋 Requirements
- Wireshark CLI tools on PATH: `tshark`, `mergecap`, `editcap`, `capinfos`
- From source: Python 3.8+ (GUI requires PySimpleGUI)

## 🧭 Migration
- New default: three-step workflow using `--workspace`
- Legacy one-shot flow preserved as `PCAPpuller_legacy.py` and `gui_pcappuller_legacy.py`
- Validate selections first: `--step 1 --dry-run` (or use GUI pattern settings)

## 🛠️ Fixes
- Eliminates 3× file size inflation caused by processing consolidated files alongside chunk files
- Ensures tmp directory is created before processing (stability improvement)

## ⚠️ Known Issues
- Ensure Wireshark CLI tools are installed and accessible in PATH
- Very large windows may still require sufficient temp/working space

## 🗒️ Full Changelog
See CHANGELOG.md for a detailed, versioned history.
