"""Price history endpoint — serves rolling buffer for sparkline seeding."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/prices/history/{ticker}")
async def price_history(ticker: str, request: Request):
    """Return last ~100 price points for the given ticker (for sparkline initial data)."""
    history: "PriceHistory" = request.app.state.price_history
    return {"ticker": ticker.upper(), "points": history.get(ticker.upper())}
