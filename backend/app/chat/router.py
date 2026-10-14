"""Chat API routes."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..db import get_db
from ..portfolio.service import execute_trade, get_portfolio, record_snapshot
from ..utils import now_iso as _now
from ..watchlist.router import MAX_WATCHLIST
from .llm import LLMResponse, build_portfolio_context, call_llm

router = APIRouter()

HISTORY_LIMIT = 20


@router.get("/chat/history")
async def chat_history():
    return await asyncio.to_thread(_get_history_sync)


def _get_history_sync() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role, content, actions, created_at FROM chat_messages "
            "WHERE user_id='default' ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
    return [
        {
            "role": r["role"],
            "content": r["content"],
            "actions": json.loads(r["actions"]) if r["actions"] else None,
            "created_at": r["created_at"],
        }
        for r in reversed(rows)
    ]


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat(body: ChatRequest, request: Request):
    cache = request.app.state.price_cache

    # 1. Build context and load history synchronously
    context_data = await asyncio.to_thread(lambda: _load_context_sync(cache))
    portfolio_context = build_portfolio_context(context_data["portfolio"], context_data["watchlist"])

    # 2. Store user message
    await asyncio.to_thread(lambda: _store_message_sync("user", body.message, None))

    # 3. Call LLM (async, may take up to 30s)
    messages = context_data["history"] + [{"role": "user", "content": body.message}]
    llm_resp: LLMResponse = await call_llm(messages, portfolio_context)

    # 4. Execute trades
    executed_trades = []
    trade_errors = []
    for trade in llm_resp.trades:
        result = await asyncio.to_thread(
            lambda t=trade: _execute_trade_sync(cache, t.ticker, t.side, t.quantity)
        )
        if result["ok"]:
            executed_trades.append(result)
        else:
            trade_errors.append(result["error"])

    # 5. Execute watchlist changes
    watchlist_changes_done = []
    for change in llm_resp.watchlist_changes:
        try:
            ticker = change.ticker.upper()
            if change.action == "add":
                added = await asyncio.to_thread(lambda t=ticker: _add_to_watchlist_sync(t))
                if added:
                    await request.app.state.market_source.add_ticker(ticker)
                    watchlist_changes_done.append({"ticker": ticker, "action": "add"})
            elif change.action == "remove":
                removed = await asyncio.to_thread(lambda t=ticker: _remove_from_watchlist_sync(t))
                if removed:
                    await request.app.state.market_source.remove_ticker(ticker)
                    watchlist_changes_done.append({"ticker": ticker, "action": "remove"})
        except Exception:
            pass

    final_message = llm_resp.message
    if trade_errors:
        final_message += "\n\nNote: " + "; ".join(trade_errors)

    actions = {"trades": executed_trades, "watchlist_changes": watchlist_changes_done}

    # 6. Store assistant message
    await asyncio.to_thread(lambda: _store_message_sync("assistant", final_message, actions))

    return {"message": final_message, "actions": actions}


# --- Sync helpers ---

def _load_context_sync(cache) -> dict:
    with get_db() as conn:
        portfolio = get_portfolio(conn, cache)
        watchlist_rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id='default' ORDER BY added_at"
        ).fetchall()
        watchlist = [{"ticker": r["ticker"], "price": cache.get_price(r["ticker"])} for r in watchlist_rows]
        history_rows = conn.execute(
            "SELECT role, content FROM chat_messages WHERE user_id='default' "
            "ORDER BY created_at DESC LIMIT ?", (HISTORY_LIMIT,)
        ).fetchall()
        history = [{"role": r["role"], "content": r["content"]} for r in reversed(history_rows)]
    return {"portfolio": portfolio, "watchlist": watchlist, "history": history}


def _store_message_sync(role: str, content: str, actions: dict | None) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4()), "default", role, content, json.dumps(actions) if actions else None, _now()),
        )


def _execute_trade_sync(cache, ticker, side, quantity) -> dict:
    with get_db() as conn:
        return execute_trade(conn, cache, ticker, side, quantity)


def _add_to_watchlist_sync(ticker: str) -> bool:
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM watchlist WHERE user_id='default'").fetchone()[0]
        if count >= MAX_WATCHLIST:
            return False
        try:
            conn.execute(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?,?,?,?)",
                (str(uuid.uuid4()), "default", ticker, _now()),
            )
            return True
        except Exception:
            return False


def _remove_from_watchlist_sync(ticker: str) -> bool:
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM watchlist WHERE user_id='default' AND ticker=?", (ticker,))
    return cursor.rowcount > 0
