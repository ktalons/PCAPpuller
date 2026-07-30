"""Recommended settings shared by the CLI and GUI.

One table keyed by window duration: short windows tolerate large merge
batches and need wide mtime slop; long windows reverse both, and switch
per-batch trimming on to cap temp-space use.
"""

from __future__ import annotations

# (max_duration_minutes, batch_size, slop_min)
_TIERS = [
    (15, 500, 120),
    (60, 400, 60),
    (240, 300, 30),
    (720, 200, 20),
]
_BEYOND = (150, 15)  # past 12 hours


def recommended_batch_size(duration_minutes: int) -> int:
    for limit, batch, _slop in _TIERS:
        if duration_minutes <= limit:
            return batch
    return _BEYOND[0]


def recommended_slop_min(duration_minutes: int) -> int:
    for limit, _batch, slop in _TIERS:
        if duration_minutes <= limit:
            return slop
    return _BEYOND[1]


def recommended_trim_per_batch(duration_minutes: int) -> bool:
    return duration_minutes > 60


def recommended_settings(duration_minutes: int) -> dict:
    return {
        "workers": "auto",
        "batch": recommended_batch_size(duration_minutes),
        "slop": recommended_slop_min(duration_minutes),
        "trim_per_batch": recommended_trim_per_batch(duration_minutes),
        "precise_filter": True,
    }
