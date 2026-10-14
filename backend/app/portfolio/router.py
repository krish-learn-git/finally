"""Portfolio API routes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..db import get_db
from .service import execute_trade, get_history, get_portfolio

router = APIRouter()


class TradeRequest(BaseModel):
    ticker: str
    side: str
    quantity: float


@router.get("/portfolio")
async def portfolio(request: Request):
    cache = request.app.state.price_cache
    return await asyncio.to_thread(lambda: _portfolio_sync(cache))


def _portfolio_sync(cache):
    with get_db() as conn:
        return get_portfolio(conn, cache)


@router.post("/portfolio/trade")
async def trade(body: TradeRequest, request: Request):
    cache = request.app.state.price_cache
    result = await asyncio.to_thread(
        lambda: _trade_sync(cache, body.ticker, body.side, body.quantity)
    )
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


def _trade_sync(cache, ticker, side, quantity):
    with get_db() as conn:
        return execute_trade(conn, cache, ticker, side, quantity)


@router.get("/portfolio/history")
async def portfolio_history():
    return await asyncio.to_thread(_history_sync)


def _history_sync():
    with get_db() as conn:
        return get_history(conn)
