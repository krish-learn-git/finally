# Code Review — Backend (October 2026)

Reviewed the current uncommitted diff against `main`. All findings are in the backend.

---

## Findings

### 1. Race condition: `add_ticker` mutates list during concurrent iteration
**File**: `backend/app/market/yfinance_client.py` line 51  
**Severity**: High  
`add_ticker` calls `self._tickers.append(ticker)` while `_fetch_prices` runs in a thread pool and iterates `self._tickers`. CPython list `append` mutates in-place; concurrent iteration raises `RuntimeError: list changed size during iteration`, crashing the poll task.  
**Fix**: Snapshot `self._tickers` into a local variable at the start of `_fetch_prices`.

---

### 2. `yfinance` not declared in `pyproject.toml`
**File**: `backend/pyproject.toml`  
**Severity**: High  
`yfinance` is imported unconditionally in `yfinance_client.py` and `test_factory.py` but is absent from `[project.dependencies]`. A clean `uv sync` or Docker build will fail with `ModuleNotFoundError`.  
**Fix**: Add `yfinance>=0.2.0` to dependencies.

---

### 3. `urllib3` used but not declared in `pyproject.toml`
**File**: `backend/app/chat/llm.py` line 66  
**Severity**: High  
`urllib3` is used directly but not listed as a dependency. It may be transitively available today but can break silently on version upgrades.  
**Fix**: Add `urllib3>=2.0.0` to dependencies.

---

### 4. `attach_history_to_cache` called after `market_source.start()`
**File**: `backend/app/main.py` line 34  
**Severity**: Medium  
`start()` calls `_poll_once()` eagerly, writing prices to the cache before `attach_history_to_cache` is patched in. The first poll cycle never reaches the history buffer, so `GET /api/prices/history/{ticker}` returns an empty list until the second poll (up to 15 s with yfinance), defeating sparkline seeding.  
**Fix**: Call `attach_history_to_cache` before `market_source.start()`.

---

### 5. `self._tickers` read twice without snapshot — sets can diverge
**File**: `backend/app/market/yfinance_client.py` line 81  
**Severity**: Medium  
`_fetch_prices` reads `self._tickers` once to build the yfinance download query (line 81) and again to parse results (line 94). A `remove_ticker` call between these two reads causes a mismatch between the downloaded data and the parse loop, producing a `TypeError` or a silently dropped price update.  
**Fix**: Capture `tickers = list(self._tickers)` once at the top of `_fetch_prices` and use that throughout.

---

### 6. Exact float equality check for zero quantity
**File**: `backend/app/portfolio/service.py` line 86  
**Severity**: Medium  
`if new_qty == 0:` uses exact float equality. Fractional share arithmetic can produce values like `1e-15` instead of `0.0`, leaving phantom positions in the database that are never cleaned up.  
**Fix**: Use `if new_qty < 1e-9:`.

---

### 7. PRAGMA calls outside `try` block — connection leaked on error
**File**: `backend/app/db/init.py` line 34  
**Severity**: Low  
`PRAGMA foreign_keys = ON` and `PRAGMA journal_mode = WAL` are called before entering the `try` block. If either raises, the connection is never closed.  
**Fix**: Move PRAGMA calls inside the `try` block.

---

### 8. `cache.get(t)` called twice per ticker in `get_watchlist`
**File**: `backend/app/watchlist/router.py` line 33  
**Severity**: Cleanup  
The filter `if (u := cache.get(t)) or True` always evaluates to `True`, so the walrus assignment is dead work. The body then re-binds `u` with a second `cache.get(t)`. Replace with a plain for-loop.

---

### 9. `_now()` duplicated across three modules
**File**: `backend/app/chat/router.py`, `backend/app/portfolio/service.py`, `backend/app/watchlist/router.py`  
**Severity**: Cleanup  
Identical one-liner defined in three places. Move to a shared `backend/app/utils.py` and import from there.

---

### 10. Stale "Massive" reference in docstring
**File**: `backend/app/market/__init__.py` line 7  
**Severity**: Minor  
Docstring still mentions "Massive" after the provider was replaced with yfinance. Update to reflect the current implementation.

---

## Summary

| # | File | Issue | Severity |
|---|------|-------|----------|
| 1 | `market/yfinance_client.py:51` | Race: add_ticker mutates list during poll iteration | High |
| 2 | `pyproject.toml` | `yfinance` not declared — clean build fails | High |
| 3 | `chat/llm.py:66` | `urllib3` not declared — silent breakage on upgrades | High |
| 4 | `main.py:34` | History patched after start(); first poll misses history | Medium |
| 5 | `market/yfinance_client.py:81` | Ticker list read twice without snapshot | Medium |
| 6 | `portfolio/service.py:86` | Exact float == 0 leaves phantom positions | Medium |
| 7 | `db/init.py:34` | PRAGMA outside try — connection leak on error | Low |
| 8 | `watchlist/router.py:33` | Double cache.get() via always-true walrus filter | Cleanup |
| 9 | `chat/router.py:23` + 2 others | `_now()` duplicated in three modules | Cleanup |
| 10 | `market/__init__.py:7` | Stale "Massive" in docstring | Minor |
