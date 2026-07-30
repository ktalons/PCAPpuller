from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional, Tuple

# Bump to force a rebuild of existing cache files (they simply repopulate)
SCHEMA_VERSION = 3

# Commit every N writes instead of per-write: one fsync per file crawls on
# large scans, and losing a partial batch only costs re-running capinfos
COMMIT_EVERY = 200

PRUNE_MAX_AGE_DAYS = 30


class CapinfosCache:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._dirty = 0
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_schema()
        self._prune()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        (version,) = cur.execute("PRAGMA user_version").fetchone()
        if version != SCHEMA_VERSION:
            cur.execute("DROP TABLE IF EXISTS entries")
            cur.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                path TEXT PRIMARY KEY,
                size INTEGER NOT NULL,
                mtime_ns INTEGER NOT NULL,
                ino INTEGER NOT NULL DEFAULT 0,
                first REAL,
                last REAL,
                updated_at REAL NOT NULL
            )
            """
        )
        self.conn.commit()

    def _prune(self, max_age_days: int = PRUNE_MAX_AGE_DAYS) -> None:
        cutoff = time.time() - max_age_days * 86400
        with self._lock:
            self.conn.execute("DELETE FROM entries WHERE updated_at < ?", (cutoff,))
            self.conn.commit()

    def get(self, path: Path) -> Optional[Tuple[float, float]]:
        try:
            st = path.stat()
        except OSError:
            return None
        with self._lock:
            cur = self.conn.cursor()
            row = cur.execute(
                "SELECT first, last FROM entries WHERE path=? AND size=? AND mtime_ns=? AND ino=?",
                (str(path), st.st_size, st.st_mtime_ns, st.st_ino),
            ).fetchone()
        if not row:
            return None
        first, last = row
        if first is None or last is None:
            return None
        return float(first), float(last)

    def set(self, path: Path, first: Optional[float], last: Optional[float]) -> None:
        try:
            st = path.stat()
        except OSError:
            return
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                "REPLACE INTO entries(path,size,mtime_ns,ino,first,last,updated_at) VALUES (?,?,?,?,?,?,?)",
                (str(path), st.st_size, st.st_mtime_ns, st.st_ino, first, last, time.time()),
            )
            self._dirty += 1
            if self._dirty >= COMMIT_EVERY:
                self.conn.commit()
                self._dirty = 0

    def clear(self) -> None:
        with self._lock:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM entries")
            self.conn.commit()
            self._dirty = 0

    def close(self) -> None:
        try:
            with self._lock:
                if self._dirty:
                    self.conn.commit()
                    self._dirty = 0
            self.conn.close()
        except Exception:
            # Cache loss is recoverable (capinfos re-runs), but say it happened
            logging.warning("capinfos cache flush failed on close", exc_info=True)


def default_cache_path() -> Path:
    # Prefer XDG_CACHE_HOME on Unix/macOS, else ~/.cache
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            base = str(Path.home() / "AppData" / "Local")
        return Path(base) / "pcappuller" / "capinfos.sqlite"
    xdg = os.environ.get("XDG_CACHE_HOME")
    base_path: Path = Path(xdg) if xdg else (Path.home() / ".cache")
    return base_path / "pcappuller" / "capinfos.sqlite"
