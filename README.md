# FinAlly — AI Trading Workstation

An AI-powered trading workstation that streams live market data, simulates portfolio trading, and integrates an LLM chat assistant that can analyze positions and execute trades via natural language.

Built entirely by coding agents as a capstone project for an agentic AI coding course.

## Features

- **Live price streaming** via SSE with green/red flash animations and sparklines
- **Simulated portfolio** — $10k virtual cash, market orders, instant fills
- **Portfolio visualizations** — heatmap (treemap), P&L chart, positions table
- **AI chat assistant** — analyzes holdings, suggests and auto-executes trades
- **Watchlist management** — up to 20 tickers, managed manually or via AI
- **Dark terminal aesthetic** — Bloomberg-inspired, data-dense layout

## Architecture

Single Docker container on port 8000:

- **Frontend**: Next.js (static export), TypeScript, Tailwind CSS, Lightweight Charts
- **Backend**: FastAPI (Python/uv), SSE streaming, SQLite
- **AI**: LiteLLM → Anthropic (`claude-3-5-haiku-20241022`) with structured outputs
- **Market data**: Built-in GBM simulator (default) or Yahoo Finance via yfinance (optional)

## Quick Start

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

# macOS/Linux
./scripts/start_mac.sh

# Windows
.\scripts\start_windows.ps1

# Or run directly with Docker
docker build -t finally .
docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally
```

Open http://localhost:8000

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for AI chat |
| `YFINANCE_ENABLED` | No | Set `true` for real market data via Yahoo Finance; omit to use simulator |
| `LLM_MOCK` | No | Set `true` for deterministic mock LLM responses (testing) |

> **Corporate network note**: Uses Anthropic API (`api.anthropic.com`) and optionally Yahoo Finance — both work on corporate networks (unlike OpenRouter or Polygon.io).

## Project Structure

```
finally/
├── frontend/    # Next.js static export
├── backend/     # FastAPI uv project
├── planning/    # Project documentation
├── test/        # Playwright E2E tests
├── db/          # SQLite volume mount (runtime)
└── scripts/     # Start/stop helpers
```
