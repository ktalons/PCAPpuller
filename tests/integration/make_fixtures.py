#!/usr/bin/env python3
"""Generate tiny pcap fixtures for the CI integration smoke test.

Writes three in-window captures and one out-of-window capture whose packet
times AND file mtimes both sit outside the smoke window, so both the mtime
prefilter and the precise filter are exercised.
"""

import os
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

GLOBAL_HEADER = struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)

# Smoke window: 2026-01-15 10:00:00 .. 10:30:00 UTC (smoke.sh runs with TZ=UTC)
WINDOW_START = int(datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc).timestamp())


def record(ts_sec: int) -> bytes:
    payload = b"\x00" * 42
    return struct.pack("<IIII", ts_sec, 0, len(payload), len(payload)) + payload


def write_pcap(path: Path, times: list[int]) -> None:
    path.write_bytes(GLOBAL_HEADER + b"".join(record(t) for t in times))
    os.utime(path, (times[-1], times[-1]))


def main(out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_pcap(out / "in_window_1.pcap", [WINDOW_START + 60, WINDOW_START + 120])
    write_pcap(out / "in_window_2.pcap", [WINDOW_START + 300, WINDOW_START + 600])
    # 3 hours earlier: outside the window and outside the 60-minute slop
    write_pcap(out / "out_of_window.pcap", [WINDOW_START - 10800, WINDOW_START - 10700])
    print(f"fixtures written to {out}")


if __name__ == "__main__":
    main(sys.argv[1])
