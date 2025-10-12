# PCAPpuller Analyst Guide

This guide shows how to extract time windows from large PCAP collections and clean captures efficiently using the three-step workflow.

---

## 1) Install and verify
- GUI (recommended): download from releases
  - https://github.com/ktalons/daPCAPpuller/releases/latest
- CLI: Python 3.8+ and Wireshark CLI tools
  - pip install pcappuller[datetime]

Verify tools:
- tshark --version
- mergecap --version

---

## 2) Core workflows

### A) Window extraction (three-step workflow)
GUI
1) Launch PCAPpuller GUI
2) Set Source directory, Start time, Duration (or End)
3) Optional: Pattern Settings, Display filter, Gzip
4) Run Workflow (Step 1 + Step 2)

CLI
- Complete workflow (recommended)
  - pcap-puller --workspace /tmp/job --source /data --start "YYYY-MM-DD HH:MM:SS" --minutes 15 --snaplen 256 --gzip
- Individual steps
  - pcap-puller --workspace /tmp/job --step 1 --source /data --start "YYYY-MM-DD HH:MM:SS" --minutes 15
  - pcap-puller --workspace /tmp/job --step 2 --resume --display-filter "dns or http"
  - pcap-puller --workspace /tmp/job --step 3 --resume --snaplen 256 --gzip
- Check status
  - pcap-puller --workspace /tmp/job --status

Notes
- Pattern filtering avoids duplicate/consolidated files and prevents size inflation
- Dry-run first: --step 1 --dry-run to validate file selection

### B) Clean an existing capture
GUI
1) Click Clean...
2) Choose input PCAP/PCAPNG
3) Select options (format conversion, reorder, snaplen, trimming, filters, split)
4) Click Clean

CLI
- Clean and optimize
  - pcap-clean --input large.pcapng --snaplen 256 --filter "tcp or udp or icmp" --split-seconds 300
- Convert and trim window
  - pcap-clean --input capture.pcapng --start "YYYY-MM-DD HH:MM:SS" --end "YYYY-MM-DD HH:MM:SS" --filter "ip.addr==192.168.1.100"

---

## 3) Pattern filtering (keep it simple)
Defaults
- Include: *.pcap, *.pcapng
- Exclude: none (add excludes only if needed)

Custom patterns
- Include examples:
  - --include-pattern "*.chunk_*.pcap" "capture_*.pcap"
- Exclude examples:
  - --exclude-pattern "*.backup.*" "*.temp.*" "*.sorted.*"

Tip: Validate with --step 1 --dry-run before running the full workflow.

---

## 4) Best practices
- Use --workspace and run the three-step workflow to avoid size inflation
- Validate selection with --step 1 --dry-run
- Use --precise-filter to skip irrelevant files on large stores
- Tune --workers to match storage throughput (auto is a good default)
- Use Step 3 cleaning for 60–90% final size reduction

---

## 5) Troubleshooting
- Tools not found: install Wireshark CLI tools and ensure PATH is set
- No candidate files: increase --slop-min, verify time window, try without --precise-filter
- Temp disk full: set --tmpdir to a larger filesystem or reduce --batch-size
- Step failures: check --status and re-run with --resume

---

## 6) Filters (a few useful examples)
- Security
  - "tls.alert.description == 21"          # TLS certificate errors
  - "http.response.code >= 400"           # HTTP errors
- Protocol
  - "dns.flags.rcode != 0"                # DNS failures
  - "icmp.type == 3"                      # Destination unreachable

Reference: Wireshark Display Filter Reference — https://www.wireshark.org/docs/dfref/

---

## 7) Status and resume
- Show progress: pcap-puller --workspace /tmp/job --status
- Resume after failure: use --resume with the next step
