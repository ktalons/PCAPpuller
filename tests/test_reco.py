"""Unit tests for pcappuller.reco tier tables."""

from __future__ import annotations

import pytest

from pcappuller.reco import (
    recommended_batch_size,
    recommended_settings,
    recommended_slop_min,
    recommended_trim_per_batch,
)

# (duration_minutes, batch, slop) across every tier boundary
TIER_CASES = [
    (1, 500, 120),
    (15, 500, 120),  # first tier upper bound
    (16, 400, 60),
    (60, 400, 60),  # second tier upper bound
    (61, 300, 30),
    (240, 300, 30),  # third tier upper bound
    (241, 200, 20),
    (720, 200, 20),  # fourth tier upper bound
    (721, 150, 15),  # beyond 12 hours
    (100000, 150, 15),
]


@pytest.mark.parametrize("duration,batch,_slop", TIER_CASES)
def test_recommended_batch_size(duration, batch, _slop):
    assert recommended_batch_size(duration) == batch


@pytest.mark.parametrize("duration,_batch,slop", TIER_CASES)
def test_recommended_slop_min(duration, _batch, slop):
    assert recommended_slop_min(duration) == slop


@pytest.mark.parametrize(
    "duration,expected",
    [(15, False), (60, False), (61, True), (720, True), (721, True)],
)
def test_recommended_trim_per_batch(duration, expected):
    assert recommended_trim_per_batch(duration) is expected


@pytest.mark.parametrize(
    "duration,batch,slop,trim",
    [
        (5, 500, 120, False),
        (15, 500, 120, False),
        (16, 400, 60, False),
        (60, 400, 60, False),
        (90, 300, 30, True),
        (720, 200, 20, True),
        (721, 150, 15, True),
        (1440, 150, 15, True),
    ],
)
def test_recommended_settings_values(duration, batch, slop, trim):
    got = recommended_settings(duration)
    assert got == {
        "workers": "auto",
        "batch": batch,
        "slop": slop,
        "trim_per_batch": trim,
        "precise_filter": True,
    }


def test_recommended_settings_shape():
    got = recommended_settings(30)
    assert set(got) == {"workers", "batch", "slop", "trim_per_batch", "precise_filter"}
    assert got["workers"] == "auto"
    assert got["precise_filter"] is True
    assert isinstance(got["batch"], int)
    assert isinstance(got["slop"], int)
    assert isinstance(got["trim_per_batch"], bool)
