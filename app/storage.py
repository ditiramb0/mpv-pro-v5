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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS paper_orders (
                order_id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                market TEXT NOT NULL CHECK(market IN ('forex', 'crypto')),
                side TEXT NOT NULL CHECK(side IN ('BUY', 'SELL')),
                entry REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                equity REAL NOT NULL,
                risk_percent REAL NOT NULL,
                risk_amount REAL NOT NULL,
                quantity_estimate REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'closed')),
                close_price REAL,
                pnl_estimate REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                closed_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_paper_orders_created_at ON paper_orders(created_at DESC)")


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


def save_paper_order(order: dict) -> bool:
    with connection() as conn:
        cursor = conn.execute("""
            INSERT OR IGNORE INTO paper_orders (
                order_id, ticker, market, side, entry, stop_loss, take_profit,
                equity, risk_percent, risk_amount, quantity_estimate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order["order_id"], order["ticker"], order["market"], order["side"],
            order["entry"], order["stop_loss"], order["take_profit"], order["equity"],
            order["risk_percent"], order["risk_amount"], order["quantity_estimate"],
        ))
        return cursor.rowcount == 1


def get_paper_order(order_id: str):
    with connection() as conn:
        row = conn.execute("SELECT * FROM paper_orders WHERE order_id = ?", (order_id,)).fetchone()
        return dict(row) if row else None


def recent_paper_orders(limit: int = 50):
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM paper_orders ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def paper_risk_state(equity: float, max_daily_loss_percent: float, max_consecutive_losses: int) -> dict:
    if equity <= 0 or max_daily_loss_percent <= 0 or max_consecutive_losses < 1:
        raise ValueError("Equity and risk limits must be positive.")
    with connection() as conn:
        daily = conn.execute(
            "SELECT COALESCE(SUM(pnl_estimate), 0) AS pnl FROM paper_orders "
            "WHERE status = 'closed' AND date(closed_at) = date('now')"
        ).fetchone()
        recent = conn.execute(
            "SELECT pnl_estimate FROM paper_orders WHERE status = 'closed' "
            "ORDER BY closed_at DESC LIMIT ?",
            (max_consecutive_losses,),
        ).fetchall()
    daily_pnl = float(daily["pnl"] or 0.0)
    loss_limit_amount = equity * max_daily_loss_percent / 100.0
    consecutive_losses = 0
    for row in recent:
        pnl = row["pnl_estimate"]
        if pnl is None or pnl >= 0:
            break
        consecutive_losses += 1
    return {
        "daily_realized_pnl_estimate": round(daily_pnl, 8),
        "daily_loss_limit_amount": round(loss_limit_amount, 8),
        "max_daily_loss_percent": max_daily_loss_percent,
        "daily_loss_limit_reached": daily_pnl <= -loss_limit_amount,
        "consecutive_losses": consecutive_losses,
        "max_consecutive_losses": max_consecutive_losses,
        "consecutive_loss_limit_reached": consecutive_losses >= max_consecutive_losses,
        "scope": "paper orders only; gross estimates excluding fees, spread, slippage and funding",
    }


def close_paper_order(order_id: str, close_price: float):
    with connection() as conn:
        row = conn.execute("SELECT * FROM paper_orders WHERE order_id = ?", (order_id,)).fetchone()
        if row is None:
            return "not_found", None
        order = dict(row)
        if order["status"] != "open":
            return "already_closed", order
        gross_pnl = (
            (close_price - order["entry"]) * order["quantity_estimate"]
            if order["side"] == "BUY"
            else (order["entry"] - close_price) * order["quantity_estimate"]
        )
        conn.execute("""
            UPDATE paper_orders
            SET status = 'closed', close_price = ?, pnl_estimate = ?, closed_at = CURRENT_TIMESTAMP
            WHERE order_id = ? AND status = 'open'
        """, (close_price, gross_pnl, order_id))
        updated = conn.execute("SELECT * FROM paper_orders WHERE order_id = ?", (order_id,)).fetchone()
        return "closed", dict(updated)
