"""Portfolio business logic — synchronous, runs via asyncio.to_thread in routes."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

from ..market.cache import PriceCache
from ..utils import now_iso as _now


def get_portfolio(conn: sqlite3.Connection, cache: PriceCache) -> dict:
    row = conn.execute("SELECT cash_balance FROM users_profile WHERE id = 'default'").fetchone()
    cash = row["cash_balance"] if row else 10000.0

    rows = conn.execute(
        "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = 'default'"
    ).fetchall()

    positions = []
    positions_value = 0.0
    for r in rows:
        ticker, qty, avg_cost = r["ticker"], r["quantity"], r["avg_cost"]
        current_price = cache.get_price(ticker) or avg_cost
        market_value = qty * current_price
        unrealized_pnl = (current_price - avg_cost) * qty
        pnl_pct = ((current_price - avg_cost) / avg_cost * 100) if avg_cost else 0.0
        positions.append({
            "ticker": ticker,
            "quantity": qty,
            "avg_cost": avg_cost,
            "current_price": current_price,
            "market_value": market_value,
            "unrealized_pnl": unrealized_pnl,
            "pnl_percent": pnl_pct,
        })
        positions_value += market_value

    return {"cash_balance": cash, "positions": positions, "total_value": cash + positions_value}


def execute_trade(
    conn: sqlite3.Connection, cache: PriceCache, ticker: str, side: str, quantity: float
) -> dict:
    ticker = ticker.upper()
    price = cache.get_price(ticker)
    if price is None:
        return {"ok": False, "error": f"No price data for {ticker}"}

    cash = conn.execute("SELECT cash_balance FROM users_profile WHERE id = 'default'").fetchone()["cash_balance"]
    pos = conn.execute(
        "SELECT quantity, avg_cost FROM positions WHERE user_id = 'default' AND ticker = ?", (ticker,)
    ).fetchone()

    if side == "buy":
        cost = price * quantity
        if cost > cash:
            return {"ok": False, "error": f"Insufficient cash (need ${cost:.2f}, have ${cash:.2f})"}
        conn.execute("UPDATE users_profile SET cash_balance = ? WHERE id = 'default'", (cash - cost,))
        if pos:
            old_qty, old_avg = pos["quantity"], pos["avg_cost"]
            new_qty = old_qty + quantity
            new_avg = (old_avg * old_qty + price * quantity) / new_qty
            conn.execute(
                "UPDATE positions SET quantity=?, avg_cost=?, updated_at=? WHERE user_id='default' AND ticker=?",
                (new_qty, new_avg, _now(), ticker),
            )
        else:
            conn.execute(
                "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) VALUES (?,?,?,?,?,?)",
                (str(uuid.uuid4()), "default", ticker, quantity, price, _now()),
            )

    elif side == "sell":
        if not pos:
            return {"ok": False, "error": f"No position in {ticker}"}
        held = pos["quantity"]
        if quantity > held:
            return {"ok": False, "error": f"Cannot sell {quantity} shares, only hold {held}"}
        conn.execute("UPDATE users_profile SET cash_balance = ? WHERE id = 'default'", (cash + price * quantity,))
        new_qty = held - quantity
        if new_qty < 1e-9:
            conn.execute("DELETE FROM positions WHERE user_id='default' AND ticker=?", (ticker,))
        else:
            conn.execute(
                "UPDATE positions SET quantity=?, updated_at=? WHERE user_id='default' AND ticker=?",
                (new_qty, _now(), ticker),
            )
    else:
        return {"ok": False, "error": f"Invalid side '{side}'"}

    conn.execute(
        "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) VALUES (?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "default", ticker, side, quantity, price, _now()),
    )
    record_snapshot(conn, cache)
    return {"ok": True, "ticker": ticker, "side": side, "quantity": quantity, "price": price}


def get_history(conn: sqlite3.Connection, limit: int = 2016) -> list[dict]:
    rows = conn.execute(
        "SELECT total_value, recorded_at FROM portfolio_snapshots WHERE user_id='default' "
        "ORDER BY recorded_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return [{"total_value": r["total_value"], "recorded_at": r["recorded_at"]} for r in reversed(rows)]


def record_snapshot(conn: sqlite3.Connection, cache: PriceCache) -> None:
    """Write a portfolio snapshot row and prune entries older than 7 days."""
    row = conn.execute("SELECT cash_balance FROM users_profile WHERE id='default'").fetchone()
    cash = row["cash_balance"] if row else 10000.0
    rows = conn.execute("SELECT ticker, quantity, avg_cost FROM positions WHERE user_id='default'").fetchall()
    positions_value = sum((cache.get_price(r["ticker"]) or r["avg_cost"]) * r["quantity"] for r in rows)
    now = _now()
    conn.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?,?,?,?)",
        (str(uuid.uuid4()), "default", cash + positions_value, now),
    )
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    conn.execute("DELETE FROM portfolio_snapshots WHERE user_id='default' AND recorded_at<?", (cutoff,))
