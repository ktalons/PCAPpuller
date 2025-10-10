# PCAPpuller - Three-Step Workflow Guide

## Overview
PCAPpuller has been enhanced with a three-step workflow that solves the file size inflation problem and provides better control over PCAP processing:

1. **Step 1: Select** - Filter and copy relevant PCAP files to workspace
2. **Step 2: Process** - Merge, trim, and filter the selected files  
3. **Step 3: Clean** - Remove headers/metadata and compress output

## Quick Start

### Complete Workflow (All Steps)
```bash
python3 PCAPpuller.py \
  --workspace /tmp/my_workspace \
  --root /path/to/pcap/directory \
  --start "2025-08-26 16:00:00" \
  --minutes 30 \
  --slop-min 100000 \
  --snaplen 128 \
  --gzip
```

### Individual Steps
```bash
# Step 1: Select files
python3 PCAPpuller.py \
  --workspace /tmp/my_workspace \
  --root /path/to/pcap/directory \
  --start "2025-08-26 16:00:00" \
  --minutes 30 \
  --slop-min 100000 \
  --step 1

# Step 2: Process selected files
python3 PCAPpuller.py \
  --workspace /tmp/my_workspace \
  --step 2 \
  --resume

# Step 3: Clean output
python3 PCAPpuller.py \
  --workspace /tmp/my_workspace \
  --step 3 \
  --resume \
  --snaplen 128 \
  --gzip

# Check workflow status
python3 PCAPpuller.py \
  --workspace /tmp/my_workspace \
  --status
```

## Key Features

### File Pattern Filtering (Step 1)
- **Include patterns**: Only process files matching these patterns
  - Default: `*.chunk_*.pcap` (includes chunk files)
- **Exclude patterns**: Skip files matching these patterns  
  - Default: `*.sorted.pcap`, `*.s256.pcap` (excludes large consolidated files)

### Example: Custom Patterns
```bash
python3 PCAPpuller.py \
  --workspace /tmp/workspace \
  --root /data/pcaps \
  --include-pattern "*.chunk_*.pcap" "capture_*.pcap" \
  --exclude-pattern "*.backup.pcap" "*.temp.*" \
  --start "2025-08-26 16:00:00" \
  --minutes 60
```

### Processing Options (Step 2)
- **Batch size**: Number of files per merge batch (default: 500)
- **Output format**: pcap or pcapng (default: pcapng)
- **Display filter**: Wireshark filter to apply
- **Trim per batch**: Trim each batch vs. final file only

### Cleaning Options (Step 3)
- **Snaplen**: Truncate packets to N bytes (saves space)
- **Convert to PCAP**: Force conversion to legacy pcap format
- **Gzip**: Compress final output

## Solving the Size Inflation Problem

### The Problem
The original issue was that PCAPpuller processed both:
- 480 chunk files (~21MB each = ~27GB total)
- 3 large consolidated files (~54GB total)

This resulted in ~81GB input being processed instead of just ~27GB.

### The Solution
Step 1's pattern filtering now automatically excludes large consolidated files:

```bash
# These patterns are the defaults - they automatically exclude problematic files
--include-pattern "*.chunk_*.pcap"
--exclude-pattern "*.sorted.pcap" "*.s256.pcap"
```

### Results Comparison
- **Original**: 27GB input → 81GB output (3x inflation)
- **New workflow**: 27GB input → 27GB output (no inflation)
- **With cleaning**: 27GB input → 2-10GB output (60-90% reduction)

## Workspace Management

Each workflow creates a workspace directory structure:
```
workspace/
├── workflow_state.json    # Workflow state and progress
├── selected/             # Step 1: Selected PCAP files
├── processed/            # Step 2: Merged/trimmed files  
├── cleaned/              # Step 3: Final cleaned files
└── tmp/                  # Temporary processing files
```

## Error Recovery

The workflow is resumable - if a step fails, you can fix the issue and resume:
```bash
# Resume from where it left off
python3 PCAPpuller.py --workspace /tmp/workspace --resume

# Or run specific steps
python3 PCAPpuller.py --workspace /tmp/workspace --step 2 --resume
```

## Advanced Examples

### Large Dataset Processing
```bash
# Process 6 hours of data with optimizations
python3 PCAPpuller.py \
  --workspace /tmp/large_job \
  --root /data/capture_2025_08_26 \
  --start "2025-08-26 12:00:00" \
  --minutes 360 \
  --slop-min 100000 \
  --batch-size 100 \
  --trim-per-batch \
  --workers 16 \
  --snaplen 256 \
  --gzip \
  --verbose
```

### Dry Run to Preview
```bash
# See what files would be selected without processing
python3 PCAPpuller.py \
  --workspace /tmp/preview \
  --root /data/pcaps \
  --start "2025-08-26 16:00:00" \
  --minutes 60 \
  --step 1 \
  --dry-run
```

### Network Analysis Workflow
```bash
# Step 1: Select HTTP traffic files
python3 PCAPpuller.py \
  --workspace /tmp/http_analysis \
  --root /data/network_logs \
  --include-pattern "*http*" "*web*" \
  --start "2025-08-26 16:00:00" \
  --minutes 120 \
  --step 1

# Step 2: Process with HTTP filter
python3 PCAPpuller.py \
  --workspace /tmp/http_analysis \
  --step 2 \
  --resume \
  --display-filter "tcp.port == 80 or tcp.port == 443"

# Step 3: Create compact analysis file  
python3 PCAPpuller.py \
  --workspace /tmp/http_analysis \
  --step 3 \
  --resume \
  --snaplen 200 \
  --convert-to-pcap \
  --gzip
```

## Status and Monitoring

```bash
# Check workflow progress
python3 PCAPpuller.py --workspace /tmp/workspace --status

# Output example:
# 📊 Workflow Status
#    Workspace: /tmp/workspace
#    Time window: 2025-08-26 16:00:00 to 2025-08-26 16:30:00
# 
#    Step 1 (Select): ✅ Complete
#             Files: 29, Size: 558.47 MB
#    Step 2 (Process): ✅ Complete
#             File: merged_20251010_145621.pcapng, Size: 558.47 MB
#    Step 3 (Clean): ✅ Complete
#             File: snaplen_20251010_145715.pcapng.gz, Size: 65.15 MB
```

## Migration from Legacy PCAPpuller

The new three-step workflow is now the default. Legacy users need to:
1. Add `--workspace` parameter (required)
2. Use pattern filters to avoid large files (automatic defaults)
3. Optionally use cleaning steps for size reduction

### Before (Legacy)
```bash
# Legacy version (caused size inflation)
python3 PCAPpuller_legacy.py \
  --root /data/pcaps \
  --start "2025-08-26 16:00:00" \
  --minutes 60 \
  --out output.pcap
```

### After (Current)
```bash
# New workflow (solves size inflation)
python3 PCAPpuller.py \
  --workspace /tmp/workspace \
  --root /data/pcaps \
  --start "2025-08-26 16:00:00" \
  --minutes 60 \
  --slop-min 100000 \
  --snaplen 256 \
  --gzip
```
