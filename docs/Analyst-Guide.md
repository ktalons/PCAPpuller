# PCAPpuller Analyst Guide v0.2.3

A comprehensive guide for SOC analysts to extract, clean, and analyze network traffic efficiently.

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

## 2. Core Workflows

### A. PCAP Window Extraction (Main Use Case)
**GUI**: Launch PCAPpuller GUI
1. Set **Root** directories containing PCAPs
2. Configure **Start time** and **Duration**  
3. Optional: Enable **Precise filter** for accuracy
4. Optional: Apply **Display filter** (300+ filters available)
5. Click **Run**

**CLI**:
```bash
# Basic extraction
pcap-puller --root /data --start "2025-10-10 14:30:00" --minutes 15 --out incident.pcapng

# Advanced with filtering
pcap-puller --root /data --start "2025-10-10 14:30:00" --minutes 15 \
  --precise-filter --workers auto --display-filter "dns or http" \
  --gzip --out analysis.pcapng.gz
```

### B. PCAP Cleaning (New in v0.2.3)
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

## 3. Advanced Filtering (300+ Filters Available)

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

## 4. Performance & Best Practices

### Storage Optimization
- **Use --tmpdir** on large volumes (NAS/SAN) if local /tmp is small
- **Enable --precise-filter** to reduce I/O by skipping irrelevant files
- **Tune --workers** to match storage throughput (start with "auto")

### Time Windows
- **Format**: `YYYY-MM-DD HH:MM:SS` (local time)
- **Duration**: Use `--minutes` or `--end` (same calendar day)
- **Precision**: Supports milliseconds with `.%f` and UTC with `Z`

### Audit & Validation
```bash
# Always validate first with dry-run
pcap-puller --root /data --start "2025-10-10 14:00:00" --minutes 30 \
  --dry-run --list-out survivors.csv --summary

# Generate detailed report
pcap-puller ... --report analysis_report.csv
```

## 5. Incident Response Workflows

### Quick Incident Extraction
1. **Identify timeframe** from SIEM/logs
2. **Run dry-run** to validate file selection
3. **Extract window** with basic filtering
4. **Clean/optimize** extracted data if needed
5. **Apply specific filters** for detailed analysis

### Large Dataset Handling
1. **Use precise filtering** to reduce dataset size early
2. **Apply coarse filters** during extraction (e.g., "tcp or udp")
3. **Clean and split** large results for easier analysis
4. **Use snaplen** to reduce payload size if headers suffice

## 6. Troubleshooting

| Problem | Solution |
|---------|----------|
| "No candidate files" | Increase `--slop-min`, verify time window, disable `--precise-filter` |
| Temp disk full | Set `--tmpdir` to larger filesystem, reduce `--batch-size` |
| Missing tools | Install Wireshark CLI tools, verify PATH |
| Slow performance | Tune `--workers`, use faster storage for `--tmpdir` |
| Memory issues | Reduce `--batch-size`, use more conservative worker count |

## 7. Security & Compliance

- **Non-destructive**: Original PCAPs remain unchanged
- **Audit trail**: Use `--verbose` for command logging
- **Validation**: Always use `--dry-run` before production runs
- **Access control**: Ensure proper file permissions on output
- **Chain of custody**: Document extraction parameters and timestamps

## 8. Integration & Automation

### SOAR Integration
```bash
# Automated incident response extraction
pcap-puller --root "$PCAP_STORAGE" --start "$INCIDENT_START" \
  --minutes "$INCIDENT_DURATION" --display-filter "$IOC_FILTER" \
  --out "/cases/$CASE_ID/network_evidence.pcapng" --verbose
```

### Batch Processing
```bash
# Process multiple timeframes
for time in "14:00:00" "14:30:00" "15:00:00"; do
  pcap-puller --root /data --start "2025-10-10 $time" --minutes 15 \
    --out "analysis_${time//:}.pcapng"
done
```

