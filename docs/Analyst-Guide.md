# PCAPpuller Analyst Guide

How to extract time windows from large PCAP collections and clean captures with
the three-step workflow.

## 1. Install and verify

| Method | Command |
|--------|---------|
| CLI via pipx | `pipx install "git+https://github.com/ktalons/PCAPpuller"` |
| CLI via Homebrew | `brew install ktalons/tap/pcappuller` |
| GUI app (macOS) | `brew install --cask ktalons/tap/pcappuller` |
| GUI binaries | <https://github.com/ktalons/PCAPpuller/releases/latest> |

Verify the Wireshark tools PCAPpuller shells out to:

```bash
mergecap --version && editcap --version && capinfos --version && tshark --version
pcap-puller --version
```

## 2. Window extraction (three-step workflow)

GUI: set Source directory, Start time, and Duration, then Run Workflow
(Steps 1+2 are on by default). Use Pattern Settings and the Filters picker as
needed. To re-run Steps 2/3 later, point the Workspace field at the existing
workspace folder and untick Step 1.

CLI:

```bash
# Complete workflow, merged window written to --out
pcap-puller --workspace /tmp/job --source /data \
  --start "2026-01-15 10:00:00" --minutes 15 --out /cases/window.pcapng

# Individual steps with resume
pcap-puller --workspace /tmp/job --step 1 --source /data --start "2026-01-15 10:00:00" --minutes 15
pcap-puller --workspace /tmp/job --step 2 --resume --display-filter "dns or http"
pcap-puller --workspace /tmp/job --step 3 --resume --snaplen 256 --gzip

# Check progress any time
pcap-puller --workspace /tmp/job --status
```

Validate selection first on big stores: `--step 1 --dry-run`.

Step 3 only runs the cleaning you ask for (`--snaplen`, `--convert-to-pcap`,
`--gzip`); with no flags it leaves the Step 2 output untouched.

## 3. Clean an existing capture

`pcap-clean` post-processes a single file: convert pcapng to pcap, reorder by
timestamp, truncate payloads, trim a window, apply a display filter, split.

```bash
# Reorder + filter + split into 5-minute chunks (payloads kept intact)
pcap-clean --input large.pcapng --filter "tcp or udp or icmp" --split-seconds 300

# Truncate payloads to headers and trim a window
pcap-clean --input capture.pcapng --snaplen 256 \
  --start "2026-01-15 10:00:00" --end "2026-01-15 10:15:00"
```

Note: `--snaplen` is off by default; passing a value irreversibly truncates
payloads in the output.

## 4. Pattern filtering

Defaults: include `*.pcap` and `*.pcapng`, no excludes. Add patterns only when
the collection mixes rolling chunks with consolidated files:

```bash
--include-pattern "*.chunk_*.pcap" --exclude-pattern "*.sorted.*" "*.backup.*"
```

## 5. Troubleshooting

| Symptom | Fix |
|---------|-----|
| "not found in PATH" at start | Install Wireshark CLI tools (`brew install wireshark` / `apt install tshark`) |
| No candidate files | Widen `--slop-min`, check the window, run `--step 1 --dry-run` |
| capinfos failures reported | Check file readability; `--no-precise-filter` skips packet-time checks |
| Temp disk full | Point `--tmpdir` at a larger filesystem or lower `--batch-size` |
| Step failed midway | `--status` to see where, then re-run with `--resume` |

Exit codes: 0 ok, 1 unexpected error, 2 bad arguments, 3 bad time window,
10 disk/temp error, 11 tool missing or failed.

## 6. Useful display filters

```text
tls.alert.description == 21     TLS certificate errors
http.response.code >= 400       HTTP errors
dns.flags.rcode != 0            DNS failures
icmp.type == 3                  Destination unreachable
```

Reference: <https://www.wireshark.org/docs/dfref/>
