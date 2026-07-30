#!/usr/bin/env bash
# End-to-end smoke test for the three-step workflow, using real Wireshark
# CLI tools. Run from the repo root with pcap-puller installed on PATH.
set -euxo pipefail

export TZ=UTC
WORK="${RUNNER_TEMP:-/tmp}/pcappuller-smoke"
rm -rf "$WORK"
mkdir -p "$WORK/src"

python3 tests/integration/make_fixtures.py "$WORK/src"

# Full three-step run; step 3 has no cleaning flags so it is a no-op
pcap-puller --workspace "$WORK/ws" --source "$WORK/src" \
  --start "2026-01-15 10:00:00" --minutes 30 --step all \
  --out "$WORK/merged.pcapng" --verbose

test -s "$WORK/merged.pcapng"

# Only the 4 in-window packets survive; the out-of-window capture is dropped
packets=$(capinfos -c -M "$WORK/merged.pcapng" | awk -F: '/Number of packets/ {gsub(/ /,"",$2); print $2}')
test "$packets" = "4"

# Steps 1-2 complete; step 3 stays pending because no cleaning was requested
pcap-puller --workspace "$WORK/ws" --status
[ "$(pcap-puller --workspace "$WORK/ws" --status | grep -c ': complete')" = "2" ]

# A later explicit cleaning request must still run (the no-op must not have
# marked step 3 complete)
pcap-puller --workspace "$WORK/ws" --step 3 --resume --gzip
test -s "$WORK/merged.pcapng.gz"
[ "$(pcap-puller --workspace "$WORK/ws" --status | grep -c ': complete')" = "3" ]

# Resume on a finished workflow is a no-op
pcap-puller --workspace "$WORK/ws" --resume --gzip | grep "Step 3 already complete"

echo "integration smoke: OK"
