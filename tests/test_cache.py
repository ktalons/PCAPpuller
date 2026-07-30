"""Unit tests for pcappuller.cache.CapinfosCache against a tmp_path sqlite db."""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

from pcappuller.cache import SCHEMA_VERSION, CapinfosCache


def _make_file(tmp_path: Path, name: str = "a.pcap", data: bytes = b"x" * 64) -> Path:
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_set_get_roundtrip(tmp_path):
    cache = CapinfosCache(tmp_path / "cache.sqlite")
    p = _make_file(tmp_path)
    cache.set(p, 100.5, 200.5)
    assert cache.get(p) == (100.5, 200.5)
    cache.close()


def test_get_none_after_size_change(tmp_path):
    cache = CapinfosCache(tmp_path / "cache.sqlite")
    p = _make_file(tmp_path)
    cache.set(p, 1.0, 2.0)
    p.write_bytes(b"y" * 128)  # size changed -> stale entry
    assert cache.get(p) is None
    cache.close()


def test_get_none_after_mtime_change(tmp_path):
    cache = CapinfosCache(tmp_path / "cache.sqlite")
    p = _make_file(tmp_path)
    cache.set(p, 1.0, 2.0)
    st = p.stat()
    os.utime(p, (st.st_atime, st.st_mtime + 10))  # same size, new mtime
    assert cache.get(p) is None
    cache.close()


def test_none_bounds_return_none(tmp_path):
    cache = CapinfosCache(tmp_path / "cache.sqlite")
    p = _make_file(tmp_path, "none.pcap")
    q = _make_file(tmp_path, "half.pcap")
    cache.set(p, None, None)
    cache.set(q, 1.0, None)
    assert cache.get(p) is None
    assert cache.get(q) is None
    cache.close()


def test_clear_empties(tmp_path):
    cache = CapinfosCache(tmp_path / "cache.sqlite")
    p = _make_file(tmp_path)
    cache.set(p, 1.0, 2.0)
    cache.clear()
    assert cache.get(p) is None
    (count,) = cache.conn.execute("SELECT COUNT(*) FROM entries").fetchone()
    assert count == 0
    cache.close()


def test_close_flushes_pending_writes(tmp_path):
    """Fewer than COMMIT_EVERY sets stay uncommitted until close() flushes them."""
    db = tmp_path / "cache.sqlite"
    cache = CapinfosCache(db)
    paths = [_make_file(tmp_path, f"f{i}.pcap") for i in range(3)]
    for i, p in enumerate(paths):
        cache.set(p, float(i), float(i + 1))
    cache.close()
    reopened = CapinfosCache(db)
    for i, p in enumerate(paths):
        assert reopened.get(p) == (float(i), float(i + 1))
    reopened.close()


def test_schema_migration_recreates_table(tmp_path):
    """An old user_version db is dropped and rebuilt at SCHEMA_VERSION."""
    db = tmp_path / "cache.sqlite"
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA user_version = 1")
    conn.execute("CREATE TABLE entries (path TEXT PRIMARY KEY, first REAL, last REAL)")
    conn.execute("INSERT INTO entries VALUES ('/old/a.pcap', 1.0, 2.0)")
    conn.commit()
    conn.close()

    cache = CapinfosCache(db)
    (version,) = cache.conn.execute("PRAGMA user_version").fetchone()
    assert version == SCHEMA_VERSION == 2
    (count,) = cache.conn.execute("SELECT COUNT(*) FROM entries").fetchone()
    assert count == 0
    p = _make_file(tmp_path)
    assert cache.get(p) is None
    cache.close()


def test_prune_drops_stale_rows(tmp_path):
    """Rows older than PRUNE_MAX_AGE_DAYS are deleted on open."""
    db = tmp_path / "cache.sqlite"
    cache = CapinfosCache(db)
    p = _make_file(tmp_path)
    cache.set(p, 1.0, 2.0)
    cache.close()

    conn = sqlite3.connect(str(db))
    conn.execute("UPDATE entries SET updated_at = ?", (time.time() - 40 * 86400,))
    conn.commit()
    conn.close()

    reopened = CapinfosCache(db)
    (count,) = reopened.conn.execute("SELECT COUNT(*) FROM entries").fetchone()
    assert count == 0
    assert reopened.get(p) is None
    reopened.close()
