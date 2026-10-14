"""Watchlist API routes."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..db import get_db
from ..utils import now_iso as _now

router = APIRouter()

MAX_WATCHLIST = 20


@router.get("/watchlist")
async def get_watchlist(request: Request):
    cache = request.app.state.price_cache
    tickers = await asyncio.to_thread(_get_tickers_sync)
    result = []
    for t in tickers:
        u = cache.get(t)
        result.append({
            "ticker": t,
            "price": u.price if u else None,
            "previous_price": u.previous_price if u else None,
            "direction": u.direction if u else "flat",
            "change_percent": u.change_percent if u else 0.0,
        })
    return result


def _get_tickers_sync() -> list[str]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id='default' ORDER BY added_at"
        ).fetchall()
    return [r["ticker"] for r in rows]


class AddTickerRequest(BaseModel):
    ticker: str


@router.post("/watchlist", status_code=201)
async def add_ticker(body: AddTickerRequest, request: Request):
    ticker = body.ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker cannot be empty")

    error = await asyncio.to_thread(lambda: _add_ticker_sync(ticker))
    if error:
        raise HTTPException(status_code=400 if "limit" in error else 409, detail=error)

    await request.app.state.market_source.add_ticker(ticker)
    return {"ticker": ticker}


def _add_ticker_sync(ticker: str) -> str | None:
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM watchlist WHERE user_id='default'").fetchone()[0]
        if count >= MAX_WATCHLIST:
            return f"Watchlist limit of {MAX_WATCHLIST} tickers reached"
        try:
            conn.execute(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?,?,?,?)",
                (str(uuid.uuid4()), "default", ticker, _now()),
            )
        except Exception:
            return f"{ticker} is already on the watchlist"
    return None


@router.delete("/watchlist/{ticker}")
async def remove_ticker(ticker: str, request: Request):
    ticker = ticker.upper().strip()
    removed = await asyncio.to_thread(lambda: _remove_ticker_sync(ticker))
    if not removed:
        raise HTTPException(status_code=404, detail=f"{ticker} not on watchlist")
    await request.app.state.market_source.remove_ticker(ticker)
    return {"ticker": ticker, "removed": True}


def _remove_ticker_sync(ticker: str) -> bool:
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM watchlist WHERE user_id='default' AND ticker=?", (ticker,)
        )
    return cursor.rowcount > 0
