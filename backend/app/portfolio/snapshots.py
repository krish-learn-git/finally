"""Background task: record portfolio snapshots every 30 seconds."""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


async def start_snapshot_task(price_cache) -> asyncio.Task:
    task = asyncio.create_task(_snapshot_loop(price_cache), name="portfolio-snapshots")
    return task


async def _snapshot_loop(price_cache) -> None:
    from ..db import get_db
    from .service import record_snapshot

    while True:
        await asyncio.sleep(30)
        try:
            await asyncio.to_thread(lambda: _snap_sync(price_cache))
        except Exception as e:
            logger.error("Snapshot task error: %s", e)


def _snap_sync(price_cache):
    from ..db import get_db
    from .service import record_snapshot
    with get_db() as conn:
        record_snapshot(conn, price_cache)
