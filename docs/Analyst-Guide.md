# PCAPpuller Analyst Guide v0.3.0

A comprehensive guide for SOC analysts to extract, clean, and analyze network traffic efficiently using the new **three-step workflow** that solves file size inflation issues.

## 1. Installation & Prerequisites

### Quick Start (Recommended)
Download GUI binaries from [releases](https://github.com/ktalons/daPCAPpuller/releases/latest):
- **Windows**: `PCAPpullerGUI-windows.exe`
- **macOS**: `PCAPpullerGUI-macos.zip` (extract .app bundle)
- **Linux**: `pcappuller-gui_X.X.X_amd64.deb` or `PCAPpullerGUI-linux`

### Requirements
- **Wireshark CLI tools**: tshark, mergecap, editcap, capinfos
- **GUI binary**: No Python required
- **From source**: Python 3.8+ and PySimpleGUI

### Verify Installation
```bash
# Check Wireshark tools
tshark --version
mergecap --version
```

### 🔧 What's New in v0.3.0
- **SIZE INFLATION FIX**: Eliminates 3x file size inflation issues
- **Three-Step Workflow**: Select → Process → Clean for better control
- **Smart Pattern Filtering**: Automatically excludes duplicate/consolidated files
- **Workspace Management**: Organized file handling with resumable operations

## 2. Core Workflows

### A. PCAP Window Extraction (Main Use Case)

#### 🔥 NEW: Three-Step Workflow (Recommended)
**Solves file size inflation issues!**

**GUI**: Launch PCAPpuller GUI
1. Set **Root** directories containing PCAPs
2. Configure **Start time** and **Duration**
3. Enable workflow steps: ☑️ Step 1, ☑️ Step 2, ☐️ Step 3 (optional)
4. Click **Pattern Settings** to configure file filtering
5. Optional: Apply **Display filter** (300+ filters available)
6. Click **Run Workflow**

**CLI**:
```bash
# Complete three-step workflow (recommended)
pcap-puller --workspace /tmp/job --root /data --start "2025-10-10 14:30:00" --minutes 15 --snaplen 256 --gzip

# Individual steps for better control
pcap-puller --workspace /tmp/job --step 1 --root /data --start "2025-10-10 14:30:00" --minutes 15  # Select & filter
pcap-puller --workspace /tmp/job --step 2 --resume --display-filter "dns or http"  # Process  
pcap-puller --workspace /tmp/job --step 3 --resume --snaplen 256 --gzip  # Clean

# Check status anytime
pcap-puller --workspace /tmp/job --status
```

#### Legacy Mode (May Cause Size Inflation)
```bash
# Use legacy mode only if needed
pcap-puller --root /data --start "2025-10-10 14:30:00" --minutes 15 --out incident.pcapng
```

### B. PCAP Cleaning (Enhanced in v0.3.0)
**GUI**: Click **"Clean..."** button
1. Select input PCAP/PCAPNG file
2. Configure cleaning options:
   - Format conversion (pcapng → pcap)
   - Packet reordering by timestamp
   - Payload truncation (snaplen)
   - Time window trimming
   - Display filtering
   - Output splitting
3. Click **"Clean"**

**CLI**:
```bash
# Clean and optimize large capture
pcap-clean --input large.pcapng --snaplen 256 \
  --filter "tcp or udp or icmp" --split-seconds 300

# Convert format and trim time window
pcap-clean --input capture.pcapng --start "2025-10-10 14:00:00" \
  --end "2025-10-10 15:00:00" --filter "ip.addr==192.168.1.100"
```

### C. Pattern Filtering (NEW - Solves Size Inflation)
The new pattern filtering automatically prevents duplicate data processing.

**Default Settings** (work for most cases):
- **Include**: `*.chunk_*.pcap` (individual time-based files)
- **Exclude**: `*.sorted.pcap`, `*.s256.pcap` (large consolidated files)

**Custom Patterns** (GUI: Pattern Settings button):
```bash
# Include specific patterns
--include-pattern "*.chunk_*.pcap" "capture_*.pcap"

# Exclude backup/temp files
--exclude-pattern "*.backup.*" "*.temp.*" "*.sorted.*"
```

**Before vs After:**
- **Before**: Processes 480 chunks (27GB) + 3 consolidated files (54GB) = 81GB total 😱
- **After**: Processes only 480 chunks (27GB) = 27GB total 🎉
- **With cleaning**: Final output 2-10GB (60-90% reduction) 🏆

## 4. Advanced Filtering (300+ Filters Available)

### Filter Categories
- **Core Protocols**: TCP, UDP, HTTP/HTTPS, DNS, IP/IPv6, ICMP
- **Security**: TLS handshakes, IPSec, SSH, anomaly detection
- **Network Services**: DHCP, FTP, SMTP, SNMP, NTP
- **Wireless**: 802.11 WiFi management, beacon analysis
- **VoIP**: SIP, RTP call analysis
- **Routing**: OSPF, BGP, EIGRP protocols
- **Monitoring**: NetFlow, sFlow traffic analysis

### Common Analyst Filters
```bash
# Security Analysis
"tcp.flags.syn == 1 and tcp.window_size < 1024"  # Potential SYN scan
"tls.alert.description == 21"                    # TLS certificate errors
"dns.qry.name matches \".*(exe|bat|scr)$\""       # Suspicious DNS queries

# Performance Analysis  
"tcp.analysis.retransmission"                    # Network issues
"http.response.code >= 400"                      # HTTP errors
"tcp.time_delta > 0.1"                          # Slow responses

# Protocol Analysis
"dns.flags.rcode != 0"                          # DNS failures
"http.request.method == POST"                    # POST requests only
"icmp.type == 3"                                # Destination unreachable
```

## 3. Workflow Benefits & Migration

### Why Use the Three-Step Workflow?

| Issue | Legacy Method | New Workflow |
|-------|---------------|---------------|
| **Size Inflation** | 27GB → 81GB (3x) | 27GB → 27GB (1x) |
| **File Selection** | Manual exclusion | Automatic pattern filtering |
| **Error Recovery** | Start over | Resume from any step |
| **Progress Tracking** | Basic | Step-by-step with status |
| **Storage Efficiency** | Poor | Organized workspace |
| **Final Size** | Large | 60-90% reduction with cleaning |

### Migration Guide
**For Existing Users:**
1. Add `--workspace` parameter (required)
2. Pattern filtering works automatically (smart defaults)
3. Legacy files preserved as `*_legacy.py`

**Command Migration:**
```bash
# OLD (may cause size inflation)
pcap-puller --root /data --start "2025-10-10 14:00:00" --minutes 30 --out result.pcap

# NEW (solves size inflation)
pcap-puller --workspace /tmp/job --root /data --start "2025-10-10 14:00:00" --minutes 30 --snaplen 256 --gzip
```

## 5. Performance & Best Practices

### Workflow Optimization
- **Use --workspace** to enable the three-step workflow and avoid size inflation
- **Pattern filtering** automatically excludes duplicate files (check with `--step 1 --dry-run`)
- **Step-by-step execution** allows better control and error recovery
- **Resume capability** continues from failed steps without restarting

### Storage Optimization  
- **Workspace management** organizes files in `{selected,processed,cleaned}` directories
- **Enable --precise-filter** to reduce I/O by skipping irrelevant files
- **Tune --workers** to match storage throughput (start with "auto")
- **Use Step 3 cleaning** for 60-90% final file size reduction

### Time Windows
- **Format**: `YYYY-MM-DD HH:MM:SS` (local time)
- **Duration**: Use `--minutes` or `--end` (same calendar day)
- **Precision**: Supports milliseconds with `.%f` and UTC with `Z`

### Audit & Validation
```bash
# NEW: Validate three-step workflow with dry-run
pcap-puller --workspace /tmp/job --step 1 --root /data --start "2025-10-10 14:00:00" --minutes 30 --dry-run

# Check workflow status
pcap-puller --workspace /tmp/job --status

# Legacy validation (if needed)
pcap-puller --root /data --start "2025-10-10 14:00:00" --minutes 30 --dry-run --list-out survivors.csv --summary
```

## 6. Incident Response Workflows

### Quick Incident Extraction (NEW Workflow)
1. **Identify timeframe** from SIEM/logs
2. **Validate selection**: `--step 1 --dry-run` to verify file filtering  
3. **Run complete workflow**: `--workspace /tmp/incident --step all`
4. **Check results**: `--workspace /tmp/incident --status`
5. **Optional refinement**: Use Step 3 cleaning for size reduction

### Legacy Quick Extraction (If Needed)
1. **Run dry-run** to validate file selection
2. **Extract window** with basic filtering  
3. **Clean/optimize** extracted data separately
4. **Apply specific filters** for detailed analysis

### Large Dataset Handling (NEW Approach)
1. **Enable three-step workflow** to avoid size inflation from the start
2. **Use pattern filtering** to exclude consolidated files automatically
3. **Step 1 validation** with `--dry-run` to verify reasonable dataset size
4. **Step 2 coarse filtering** during processing (e.g., "tcp or udp")
5. **Step 3 optimization** with snaplen and compression for final output
6. **Resume capability** handles interruptions gracefully

## 7. Troubleshooting

| Problem | Solution |
|---------|----------|
| **Size inflation (3x)** | **Use new workflow**: add `--workspace`, pattern filtering prevents this |
| "No candidate files" | Run `--step 1 --dry-run` to debug, increase `--slop-min`, verify time window |
| Temp disk full | Workspace management handles this better, or use larger filesystem |
| Missing tools | Install Wireshark CLI tools, verify PATH |
| Slow performance | Use `--resume` to continue failed runs, tune `--workers` |
| Step failures | Use `--status` to check progress, `--resume` to continue from any step |
| Memory issues | Use three-step workflow for better memory management |

## 8. Security & Compliance

- **Non-destructive**: Original PCAPs remain unchanged
- **Audit trail**: Use `--verbose` for command logging
- **Validation**: Always use `--dry-run` before production runs
- **Access control**: Ensure proper file permissions on output
- **Chain of custody**: Document extraction parameters and timestamps

## 9. Integration & Automation

### SOAR Integration
```bash
# NEW: Automated incident response with three-step workflow
pcap-puller --workspace "/cases/$CASE_ID/workspace" --root "$PCAP_STORAGE" \
  --start "$INCIDENT_START" --minutes "$INCIDENT_DURATION" \
  --display-filter "$IOC_FILTER" --snaplen 256 --gzip --verbose

# Legacy method (if needed)
pcap-puller --root "$PCAP_STORAGE" --start "$INCIDENT_START" \
  --minutes "$INCIDENT_DURATION" --display-filter "$IOC_FILTER" \
  --out "/cases/$CASE_ID/network_evidence.pcapng" --verbose
```

### Batch Processing
```bash
# NEW: Process multiple timeframes with three-step workflow
for time in "14:00:00" "14:30:00" "15:00:00"; do
  pcap-puller --workspace "/tmp/batch_${time//:}" --root /data \
    --start "2025-10-10 $time" --minutes 15 --snaplen 256 --gzip
done

# Legacy batch processing (if needed)
for time in "14:00:00" "14:30:00" "15:00:00"; do
  pcap-puller --root /data --start "2025-10-10 $time" --minutes 15 \
    --out "analysis_${time//:}.pcapng"
done
```

