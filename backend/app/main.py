"""FinAlly — FastAPI application entry point."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

load_dotenv(Path(__file__).parent.parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

from .db import init_db
from .market import PriceCache, create_market_data_source, create_stream_router
from .market.history import PriceHistory, attach_history_to_cache

price_cache = PriceCache()
price_history = PriceHistory(max_points=100)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = os.environ.get("DB_PATH", "/app/db/finally.db")
    init_db(db_path)  # synchronous — fast, called once

    market_source = create_market_data_source(price_cache)
    from .db.init import DEFAULT_TICKERS

    attach_history_to_cache(price_cache, price_history)
    await market_source.start(DEFAULT_TICKERS)

    app.state.price_cache = price_cache
    app.state.price_history = price_history
    app.state.market_source = market_source

    from .portfolio.snapshots import start_snapshot_task
    app.state.snapshot_task = await start_snapshot_task(price_cache)

    logger.info("FinAlly backend started")
    yield

    await market_source.stop()
    task = app.state.snapshot_task
    if task and not task.done():
        task.cancel()
    logger.info("FinAlly backend stopped")


app = FastAPI(title="FinAlly", lifespan=lifespan)

from .market.history_router import router as history_router
from .portfolio.router import router as portfolio_router
from .watchlist.router import router as watchlist_router
from .chat.router import router as chat_router

app.include_router(create_stream_router(price_cache), prefix="/api")
app.include_router(portfolio_router, prefix="/api")
app.include_router(watchlist_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(history_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


_static_dir = Path(__file__).parent.parent / "static"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
