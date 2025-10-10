# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project adheres to Semantic Versioning.

## [v0.3.0] - 2025-10-10

### Highlights
- NEW three-step workflow (Select → Process → Clean) with workspace management
- Smart pattern filtering that eliminates 3× file size inflation
- Updated GUI with Pattern Settings, advanced controls, and step-by-step progress

### Added
- ThreeStepWorkflow with workspace structure: selected/, processed/, cleaned/, tmp/
- CLI (PCAPpuller.py):
  - `--workspace`, `--step {1,2,3,all}`, `--resume`, `--status`
  - Pattern controls: `--include-pattern`, `--exclude-pattern`
  - Processing controls: `--batch-size`, `--out-format`, `--display-filter`, `--trim-per-batch`
  - Cleaning options: `--snaplen`, `--convert-to-pcap`, `--gzip`
- GUI (gui_pcappuller.py):
  - Three-step workflow controls (run Step 1/2/3)
  - Pattern Settings dialog (include/exclude patterns)
  - Advanced Settings (workers, slop, batch size, trim-per-batch)
  - Current step indicator and progress callbacks
- Documentation:
  - WORKFLOW_GUIDE.md (how-to for the new workflow)
  - MIGRATION_SUMMARY.md
  - README.md and docs/Analyst-Guide.md rewritten for v0.3.0

### Changed
- Default UX is the new three-step workflow; legacy one-shot flow is preserved separately
- Improved temporary directory handling (ensures tmp directory exists before processing)

### Fixed
- Eliminates file size inflation caused by processing both chunk files and consolidated files simultaneously
- Ensures stable operation across large windows with batch trimming and status/resume

### Deprecated
- Legacy one-shot CLI/GUI usage remains available as `*_legacy.py` but is no longer the default

### Removed
- N/A


## [v0.2.3] - 2025-XX-XX

### Highlights
- Massive Wireshark filter expansion (300+ filters across 41 protocol categories)
- GUI "Clean" integration with convert/reorder/snaplen/filter/split
- Desktop integration (icons, desktop files for Linux packages)
- Enhanced CI/CD and testing

