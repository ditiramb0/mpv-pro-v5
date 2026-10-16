from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import settings

def _sqlite_path() -> str:
    prefix = "sqlite:///"
    if not settings.database_url.startswith(prefix):
        raise RuntimeError("This starter storage layer currently supports SQLite only.")
    return settings.database_url[len(prefix):]

@contextmanager
def connection():
    path = _sqlite_path()
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def initialize_database() -> None:
    with connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                signal_id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                market TEXT NOT NULL DEFAULT 'crypto' CHECK(market IN ('forex', 'crypto')),
                action TEXT NOT NULL CHECK(action IN ('BUY', 'SELL')),
                timeframe TEXT NOT NULL,
                entry REAL,
                stop_loss REAL,
                received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'received'
            )
        """)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(signals)").fetchall()}
        if "market" not in columns:
            conn.execute("ALTER TABLE signals ADD COLUMN market TEXT NOT NULL DEFAULT 'crypto'")

def save_signal(signal) -> bool:
    with connection() as conn:
        cursor = conn.execute("""
            INSERT OR IGNORE INTO signals
                (signal_id, ticker, market, action, timeframe, entry, stop_loss)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (signal.signal_id, signal.ticker, signal.market, signal.action,
              signal.timeframe, signal.entry, signal.stop_loss))
        return cursor.rowcount == 1

def recent_signals(limit: int = 50):
    with connection() as conn:
        rows = conn.execute(
            "SELECT signal_id, ticker, market, action, timeframe, entry, stop_loss, received_at, status "
            "FROM signals ORDER BY received_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
