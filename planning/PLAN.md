# FinAlly — AI Trading Workstation

## Project Specification

## 1. Vision

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot.

This is the capstone project for an agentic AI coding course. It is built entirely by Coding Agents demonstrating how orchestrated AI agents can produce a production-quality full-stack application. Agents interact through files in `planning/`.

## 2. User Experience

### First Launch

The user runs a single Docker command (or a provided start script). A browser opens to `http://localhost:8000`. No login, no signup. They immediately see:

- A watchlist of 10 default tickers with live-updating prices in a grid
- $10,000 in virtual cash
- A dark, data-rich trading terminal aesthetic
- An AI chat panel ready to assist

### What the User Can Do

- **Watch prices stream** — prices flash green (uptick) or red (downtick) with subtle CSS animations that fade
- **View sparkline mini-charts** — price action beside each ticker in the watchlist, accumulated on the frontend from the SSE stream since page load (sparklines fill in progressively)
- **Click a ticker** to see a larger detailed chart in the main chart area
- **Buy and sell shares** — market orders only, instant fill at current price, no fees, no confirmation dialog
- **Monitor their portfolio** — a heatmap (treemap) showing positions sized by weight and colored by P&L, plus a P&L chart tracking total portfolio value over time
- **View a positions table** — ticker, quantity, average cost, current price, unrealized P&L, % change
- **Chat with the AI assistant** — ask about their portfolio, get analysis, and have the AI execute trades and manage the watchlist through natural language
- **Manage the watchlist** — add/remove tickers manually or via the AI chat

### Visual Design

- **Dark theme**: backgrounds around `#0d1117` or `#1a1a2e`, muted gray borders, no pure black
- **Price flash animations**: brief green/red background highlight on price change, fading over ~500ms via CSS transitions
- **Connection status indicator**: a small colored dot (green = connected, yellow = reconnecting, red = disconnected) visible in the header
- **Professional, data-dense layout**: inspired by Bloomberg/trading terminals — every pixel earns its place
- **Responsive but desktop-first**: optimized for wide screens, functional on tablet

### Color Scheme
- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991` (submit buttons)

## 3. Architecture Overview

### Single Container, Single Port

```
┌─────────────────────────────────────────────────┐
│  Docker Container (port 8000)                   │
│                                                 │
│  FastAPI (Python/uv)                            │
│  ├── /api/*          REST endpoints             │
│  ├── /api/stream/*   SSE streaming              │
│  └── /*              Static file serving         │
│                      (Next.js export)            │
│                                                 │
│  SQLite database (volume-mounted)               │
│  Background task: market data polling/sim        │
└─────────────────────────────────────────────────┘
```

- **Frontend**: Next.js with TypeScript, built as a static export (`output: 'export'`), served by FastAPI as static files
- **Backend**: FastAPI (Python), managed as a `uv` project
- **Database**: SQLite, single file at `db/finally.db`, volume-mounted for persistence
- **Real-time data**: Server-Sent Events (SSE) — simpler than WebSockets, one-way server→client push, works everywhere
- **AI integration**: LiteLLM → Anthropic (Claude 3.5 Haiku for fast inference), with structured outputs for trade execution
- **Market data**: Environment-variable driven — simulator by default, real data via yfinance (Yahoo Finance) if `YFINANCE_ENABLED=true`

### Why These Choices

| Decision | Rationale |
|---|---|
| SSE over WebSockets | One-way push is all we need; simpler, no bidirectional complexity, universal browser support |
| Static Next.js export | Single origin, no CORS issues, one port, one container, simple deployment |
| SQLite over Postgres | No auth = no multi-user = no need for a database server; self-contained, zero config |
| Single Docker container | Students run one command; no docker-compose for production, no service orchestration |
| uv for Python | Fast, modern Python project management; reproducible lockfile; what students should learn |
| Market orders only | Eliminates order book, limit order logic, partial fills — dramatically simpler portfolio math |

---

## 4. Directory Structure

```
finally/
├── frontend/                 # Next.js TypeScript project (static export)
├── backend/                  # FastAPI uv project (Python)
│   └── db/                   # Schema definitions, seed data, migration logic
├── planning/                 # Project-wide documentation for agents
│   ├── PLAN.md               # This document
│   └── ...                   # Additional agent reference docs
├── scripts/
│   ├── start_mac.sh          # Launch Docker container (macOS/Linux)
│   ├── stop_mac.sh           # Stop Docker container (macOS/Linux)
│   ├── start_windows.ps1     # Launch Docker container (Windows PowerShell)
│   └── stop_windows.ps1      # Stop Docker container (Windows PowerShell)
├── test/                     # Playwright E2E tests + docker-compose.test.yml
├── db/                       # Volume mount target (SQLite file lives here at runtime)
│   └── .gitkeep              # Directory exists in repo; finally.db is gitignored
├── Dockerfile                # Multi-stage build (Node → Python)
├── .env                      # Environment variables (gitignored, .env.example committed)
└── .gitignore
```

### Key Boundaries

- **`frontend/`** is a self-contained Next.js project. It knows nothing about Python. It talks to the backend via `/api/*` endpoints and `/api/stream/*` SSE endpoints. Internal structure is up to the Frontend Engineer agent.
- **`backend/`** is a self-contained uv project with its own `pyproject.toml`. It owns all server logic including database initialization, schema, seed data, API routes, SSE streaming, market data, and LLM integration. Internal structure is up to the Backend/Market Data agents.
- **`backend/db/`** contains schema SQL definitions and seed logic. The backend lazily initializes the database on first request — creating tables and seeding default data if the SQLite file doesn't exist or is empty.
- **`db/`** at the top level is the runtime volume mount point. The SQLite file (`db/finally.db`) is created here by the backend and persists across container restarts via Docker volume.
- **`planning/`** contains project-wide documentation, including this plan. All agents reference files here as the shared contract.
- **`test/`** contains Playwright E2E tests and supporting infrastructure (e.g., `docker-compose.test.yml`). Unit tests live within `frontend/` and `backend/` respectively, following each framework's conventions.
- **`scripts/`** contains start/stop scripts that wrap Docker commands.

---

## 5. Environment Variables

```bash
# Required: Anthropic API key for LLM chat functionality
# Get your key at https://console.anthropic.com/
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Optional: Enable real market data via yfinance (Yahoo Finance — free, no API key needed)
# Set to "true" to use real data; leave empty or "false" to use the built-in simulator
# NOTE: yfinance fetches from Yahoo Finance over HTTPS (port 443) — works on most corporate networks
# The simulator is recommended for demos and offline use
YFINANCE_ENABLED=false

# Optional: Set to "true" for deterministic mock LLM responses (testing)
LLM_MOCK=false
```

### Behavior

- If `YFINANCE_ENABLED=true` → backend polls Yahoo Finance via the `yfinance` library (free, no API key, ~15s interval to respect Yahoo rate limits)
- If `YFINANCE_ENABLED` is absent, empty, or `false` → backend uses the built-in market simulator (default, recommended)
- If `LLM_MOCK=true` → backend returns deterministic mock LLM responses (for E2E tests)
- The backend reads `.env` from the project root (mounted into the container or read via docker `--env-file`)

> **Corporate network note**: OpenRouter and Polygon.io (Massive) are commonly blocked by enterprise firewalls. This project uses Anthropic API (HTTPS to `api.anthropic.com`) and optionally Yahoo Finance (HTTPS to `query1.finance.yahoo.com`) — both work on corporate networks.

---

## 6. Market Data

### Two Implementations, One Interface

Both the simulator and the Massive client implement the same abstract interface. The backend selects which to use based on the environment variable. All downstream code (SSE streaming, price cache, frontend) is agnostic to the source.

### Simulator (Default)

- Generates prices using geometric Brownian motion (GBM) with configurable drift and volatility per ticker
- Updates at ~500ms intervals
- Correlated moves across tickers (e.g., tech stocks move together)
- Occasional random "events" — sudden 2-5% moves on a ticker for drama
- Starts from realistic seed prices (e.g., AAPL ~$190, GOOGL ~$175, etc.)
- Runs as an in-process background task — no external dependencies

### yfinance API (Optional Real Data — replaces Massive/Polygon.io)

- Uses the `yfinance` Python library — free, no API key, fetches from Yahoo Finance over standard HTTPS
- Works through corporate firewalls (Yahoo Finance is rarely restricted)
- Polls for the union of all watched tickers on a ~15 second interval (respects Yahoo rate limits)
- Enabled by setting `YFINANCE_ENABLED=true` in `.env`
- Parses yfinance response into the same `PriceUpdate` format as the simulator
- **Installation**: `uv add yfinance` (add to `backend/pyproject.toml`)
- **Note**: During market hours returns real last-trade prices; outside market hours returns previous close. For demo purposes this is fine — the simulator is better for live-streaming animation.

### Shared Price Cache

- A single background task (simulator or yfinance poller) writes to an in-memory price cache
- The cache holds the latest price, previous price, and timestamp for each ticker
- SSE streams read from this cache and push updates to connected clients
- This architecture supports future multi-user scenarios without changes to the data layer

### SSE Streaming

- Endpoint: `GET /api/stream/prices`
- Long-lived SSE connection; client uses native `EventSource` API
- Server pushes price updates for all tickers known to the system at a regular cadence (~500ms) — in the single-user model this is equivalent to the user's watchlist
- Each SSE event contains ticker, price, previous price, timestamp, and change direction
- Client handles reconnection automatically (EventSource has built-in retry)

---

## 7. Database

### SQLite with Lazy Initialization

The backend checks for the SQLite database on startup (or first request). If the file doesn't exist or tables are missing, it creates the schema and seeds default data. This means:

- No separate migration step
- No manual database setup
- Fresh Docker volumes start with a clean, seeded database automatically

### Schema

All tables include a `user_id` column defaulting to `"default"`. This is hardcoded for now (single-user) but enables future multi-user support without schema migration.

**users_profile** — User state (cash balance)
- `id` TEXT PRIMARY KEY (default: `"default"`)
- `cash_balance` REAL (default: `10000.0`)
- `created_at` TEXT (ISO timestamp)

**watchlist** — Tickers the user is watching
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `added_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**positions** — Current holdings (one row per ticker per user)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `quantity` REAL (fractional shares supported)
- `avg_cost` REAL
- `updated_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**trades** — Trade history (append-only log)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `side` TEXT (`"buy"` or `"sell"`)
- `quantity` REAL (fractional shares supported)
- `price` REAL
- `executed_at` TEXT (ISO timestamp)

**portfolio_snapshots** — Portfolio value over time (for P&L chart). Recorded every 30 seconds by a background task, and immediately after each trade execution. **Retention: 7 days** — snapshots older than 7 days are pruned on startup and after each insert.
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `total_value` REAL
- `recorded_at` TEXT (ISO timestamp)

**chat_messages** — Conversation history with LLM
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `role` TEXT (`"user"` or `"assistant"`)
- `content` TEXT
- `actions` TEXT (JSON — trades executed, watchlist changes made; null for user messages)
- `created_at` TEXT (ISO timestamp)

### Sell Behaviour

When a position is fully sold (quantity reaches 0), the row is **deleted** from the `positions` table. Active holdings only. Full trade history is preserved in the `trades` table.

### Default Seed Data

- One user profile: `id="default"`, `cash_balance=10000.0`
- Ten watchlist entries: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX

---

## 8. API Endpoints

### Watchlist Rules
- Maximum **20 tickers**. `POST /api/watchlist` returns HTTP 400 if the limit is already reached.
- Ticker input is plain text (e.g. `AAPL`). No autocomplete or server-side ticker validation — invalid tickers simply receive no price data.

### Market Data
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stream/prices` | SSE stream of live price updates |
| GET | `/api/prices/history/{ticker}` | Last ~100 price points from rolling in-memory buffer (for sparkline initial data on page load) |

### Portfolio
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/portfolio` | Current positions, cash balance, total value, unrealized P&L |
| POST | `/api/portfolio/trade` | Execute a trade: `{ticker, quantity, side}` |
| GET | `/api/portfolio/history` | Portfolio value snapshots over time (for P&L chart) |

### Watchlist
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/watchlist` | Current watchlist tickers with latest prices |
| POST | `/api/watchlist` | Add a ticker: `{ticker}` |
| DELETE | `/api/watchlist/{ticker}` | Remove a ticker |

### Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Send a message, receive complete JSON response (message + executed actions) |
| GET | `/api/chat/history` | Last N chat messages (for restoring conversation on page refresh) |

### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check (for Docker/deployment) |

---

## 9. LLM Integration

When writing code to make calls to LLMs, use LiteLLM with the Anthropic provider directly. Use `claude-3-5-haiku-20241022` for fast inference (comparable to Cerebras speed). Structured Outputs via Pydantic BaseModel should be used to interpret the results.

There is an ANTHROPIC_API_KEY in the .env file in the project root.

> **Why Anthropic instead of OpenRouter/Cerebras**: OpenRouter is blocked on Infosys corporate networks. Anthropic's API (`api.anthropic.com`) is accessible from corporate networks and the user already has an API key via Claude Code.

### How It Works

When the user sends a chat message, the backend:

1. Loads the user's current portfolio context (cash, positions with P&L, watchlist with live prices, total portfolio value)
2. Loads the last **20 messages** from `chat_messages` (10 exchanges) — bounds token usage and keeps latency predictable
3. Constructs a prompt with a system message, portfolio context, conversation history, and the user's new message
4. Calls the LLM via LiteLLM → Anthropic (`claude-3-5-haiku-20241022`), requesting structured output
5. Parses the complete structured JSON response
6. Auto-executes any trades or watchlist changes specified in the response
7. Stores the message and executed actions in `chat_messages`
8. Returns the complete JSON response to the frontend (no token-by-token streaming — Claude Haiku inference is fast enough that a loading indicator is sufficient)

### Structured Output Schema

The LLM is instructed to respond with JSON matching this schema:

```json
{
  "message": "Your conversational response to the user",
  "trades": [
    {"ticker": "AAPL", "side": "buy", "quantity": 10}
  ],
  "watchlist_changes": [
    {"ticker": "PYPL", "action": "add"}
  ]
}
```

- `message` (required): The conversational text shown to the user
- `trades` (optional): Array of trades to auto-execute. Each trade goes through the same validation as manual trades (sufficient cash for buys, sufficient shares for sells)
- `watchlist_changes` (optional): Array of watchlist modifications

### Auto-Execution

Trades specified by the LLM execute automatically — no confirmation dialog. This is a deliberate design choice:
- It's a simulated environment with fake money, so the stakes are zero
- It creates an impressive, fluid demo experience
- It demonstrates agentic AI capabilities — the core theme of the course

If a trade fails validation (e.g., insufficient cash), the error is included in the `message` field of the response so the LLM can inform the user naturally.

### LLM Timeout & Error Handling

- **Timeout**: 30 seconds. If the Anthropic call exceeds this, the backend returns a structured error response: `{"message": "I'm having trouble connecting right now. Please try again.", "trades": [], "watchlist_changes": []}`.
- **Parse failure**: If structured-output parsing fails entirely, return the same error shape above — never expose raw exception text to the frontend.

### System Prompt Guidance

The LLM should be prompted as "FinAlly, an AI trading assistant" with instructions to:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest trades with reasoning
- Execute trades when the user asks or agrees
- Manage the watchlist proactively
- Be concise and data-driven in responses
- Always respond with valid structured JSON

### LLM Mock Mode

When `LLM_MOCK=true`, the backend returns deterministic mock responses instead of calling Anthropic. This enables:
- Fast, free, reproducible E2E tests
- Development without an API key
- CI/CD pipelines

---

## 10. Frontend Design

### Layout

The frontend is a single-page application with a dense, terminal-inspired layout. The specific component architecture and layout system is up to the Frontend Engineer, but the UI should include these elements:

- **Watchlist panel** — grid/table of watched tickers with: ticker symbol, current price (flashing green/red on change), daily change %, and a sparkline mini-chart (accumulated from SSE since page load)
- **Main chart area** — larger chart for the currently selected ticker, with at minimum price over time. Clicking a ticker in the watchlist selects it here.
- **Portfolio heatmap** — treemap visualization where each rectangle is a position, sized by portfolio weight, colored by P&L (green = profit, red = loss)
- **P&L chart** — line chart showing total portfolio value over time, using data from `portfolio_snapshots`
- **Positions table** — tabular view of all positions: ticker, quantity, avg cost, current price, unrealized P&L, % change
- **Trade bar** — simple input area: ticker field, quantity field, buy button, sell button. Market orders, instant fill.
- **AI chat panel** — docked/collapsible sidebar. Message input, scrolling conversation history, loading indicator while waiting for LLM response. Trade executions and watchlist changes shown inline as confirmations.
- **Header** — portfolio total value (updating live), connection status indicator, cash balance

### Technical Notes

- Use `EventSource` for SSE connection to `/api/stream/prices`
- **Lightweight Charts** (TradingView) for all charts — canvas-based, high-performance, real trading-terminal aesthetic. Do not use Recharts.
- Price flash effect: on receiving a new price, briefly apply a CSS class with background color transition, then remove it
- All API calls go to the same origin (`/api/*`) — no CORS configuration needed
- Tailwind CSS for styling with a custom dark theme

---

## 11. Docker & Deployment

### Multi-Stage Dockerfile

```
Stage 1: Node 20 slim
  - Copy frontend/
  - npm install && npm run build (produces static export)

Stage 2: Python 3.12 slim
  - Install uv
  - Copy backend/
  - uv sync (install Python dependencies from lockfile)
  - Copy frontend build output into a static/ directory
  - Expose port 8000
  - CMD: uvicorn serving FastAPI app
```

> **Corporate network note (Infosys)**: PyPI (`pypi.org`) and npm (`registry.npmjs.org`) may return 403 on the Infosys network. Docker `build` runs inside the Docker daemon — if Docker is configured with host networking or a proxy, the build may succeed even when direct `pip`/`npm` commands fail from the terminal. If Docker builds fail, set `--network host` or configure the internal Nexus/Artifactory proxy (`UV_INDEX_URL`, `npm config set registry`).

FastAPI serves the static frontend files and all API routes on port 8000.

### Docker Volume

The SQLite database persists via a named Docker volume:

```bash
docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally
```

The `db/` directory in the project root maps to `/app/db` in the container. The backend writes `finally.db` to this path.

### Start/Stop Scripts

**`scripts/start_mac.sh`** (macOS/Linux):
- Builds the Docker image if not already built (or if `--build` flag passed)
- Runs the container with the volume mount, port mapping, and `.env` file
- Prints the URL to access the app
- Optionally opens the browser

**`scripts/stop_mac.sh`** (macOS/Linux):
- Stops and removes the running container
- Does NOT remove the volume (data persists)

**`scripts/start_windows.ps1`** / **`scripts/stop_windows.ps1`**: PowerShell equivalents for Windows.

All scripts should be idempotent — safe to run multiple times.

### No root docker-compose.yml

The root `docker-compose.yml` has been removed. The start/stop scripts in `scripts/` handle local development. `docker-compose.test.yml` in `test/` handles E2E testing infrastructure. No third file needed.

### Optional Cloud Deployment

The container is designed to deploy to AWS App Runner, Render, or any container platform. A Terraform configuration for App Runner may be provided in a `deploy/` directory as a stretch goal, but is not part of the core build.

---

## 12. Testing Strategy

### Unit Tests (within `frontend/` and `backend/`)

**Backend (pytest)**:
- Market data: simulator generates valid prices, GBM math is correct, yfinance response parsing works, both implementations conform to the abstract interface
- Portfolio: trade execution logic, P&L calculations, edge cases (selling more than owned, buying with insufficient cash, selling at a loss)
- LLM: structured output parsing handles all valid schemas, graceful handling of malformed responses, trade validation within chat flow
- API routes: correct status codes, response shapes, error handling

**Frontend (React Testing Library or similar)**:
- Component rendering with mock data
- Price flash animation triggers correctly on price changes
- Watchlist CRUD operations
- Portfolio display calculations
- Chat message rendering and loading state

### E2E Tests (in `test/`)

**Infrastructure**: `pytest` + `httpx` (async HTTP client) — no browser binary downloads required, works on corporate networks. Tests run against a live backend instance (started locally or in Docker) via plain HTTP calls. `docker-compose.test.yml` in `test/` spins up the app container for the test run.

**Why not Playwright**: Playwright downloads Chromium/Firefox binaries (~300MB) from external CDNs, which may be blocked on corporate networks (e.g., Infosys). `httpx` covers all the scenarios below with zero binary dependencies.

**Environment**: Tests run with `LLM_MOCK=true` by default for speed and determinism.

**LLM Mock response** (fixed, deterministic):
```json
{"message": "I've bought 5 shares of AAPL for you.", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 5}], "watchlist_changes": []}
```
This ensures the E2E scenario "trade execution appears inline" is reproducible across environments.

**Key scenarios tested via HTTP**:
- Fresh start: health check passes, default watchlist appears, $10k balance returned
- Add and remove a ticker from the watchlist
- Buy shares: cash decreases, position appears, portfolio updates
- Sell shares: cash increases, position updates or disappears
- Portfolio history: snapshots accumulate after trades
- AI chat (mocked): POST /api/chat returns response with trade, trade appears in positions
- SSE stream: connect, receive at least one price event within 2 seconds

### GitHub Actions CI

A `.github/workflows/ci.yml` is in scope. It runs on every push:
1. Backend: `uv sync --extra dev && uv run pytest`
2. Frontend: `npm ci && npm run build`

E2E `httpx` tests run in CI using `docker-compose.test.yml` — no browser install step required.

**Key Scenarios**:
- Fresh start: default watchlist appears, $10k balance shown, prices are streaming
- Add and remove a ticker from the watchlist
- Buy shares: cash decreases, position appears, portfolio updates
- Sell shares: cash increases, position updates or disappears
- Portfolio visualization: heatmap renders with correct colors, P&L chart has data points
- AI chat (mocked): send a message, receive a response, trade execution appears inline
- SSE resilience: disconnect and verify reconnection

---

## 13. Document Review — Resolved Decisions

> All items below were raised by the doc-review pass and resolved via interactive review with the project owner. Decisions are recorded here for traceability; corresponding plan sections have been updated.

| # | Question / Opportunity | Decision |
|---|---|---|
| 1 | Sparklines reset on refresh — add price history endpoint? | **Yes** — `GET /api/prices/history/{ticker}` added (rolling 100-point in-memory buffer) |
| 2 | Max watchlist size? | **20 tickers** — API returns HTTP 400 if exceeded |
| 3 | Ticker input: autocomplete or plain text? | **Plain text** — no server-side validation, simpler |
| 4 | yfinance poller vs simulator UX gap (15s vs 500ms) | **Noted** — yfinance labelled "delayed real data", simulator remains default/recommended |
| 5 | portfolio_snapshots growing forever? | **7-day retention** — prune on startup and after each insert |
| 6 | How many messages in LLM context? | **Last 20 messages** (10 exchanges) |
| 7 | Fully-sold position: delete row or keep at qty=0? | **Delete the row** — positions table = active holdings only |
| 8 | `/api/portfolio/history` pagination? | **Deferred** — 7-day retention bounds the result set sufficiently for now |
| 9 | `GET /api/chat/history` to restore on refresh? | **Yes** — endpoint added; frontend loads history on mount |
| 10 | Single-ticker price endpoint for trade bar? | **Not needed** — frontend reads current price from SSE stream state |
| 11 | LLM call timeout? | **30 seconds** — returns graceful error JSON on timeout or parse failure |
| 12 | Trade validation error: where does it surface? | **`message` field** — LLM informs user naturally in conversation |
| 13 | Charting library — Lightweight Charts or Recharts? | **Lightweight Charts** (TradingView canvas library) |
| 14 | Clicking ticker auto-populates trade bar? | **Yes** — implied by UX; explicitly noted in Frontend section |
| 15 | Heatmap empty state? | **Placeholder text**: "No positions yet — buy something!" |
| 16 | Root `docker-compose.yml` — keep or remove? | **Removed** — start/stop scripts + `docker-compose.test.yml` are sufficient |
| 17 | Where is `StaticFiles` mounted in FastAPI? | **In `app/main.py`** — `app.mount("/", StaticFiles(directory="static", html=True))` after all API routes |
| 18 | Frontend test library? | **React Testing Library** — standard for Next.js/React |
| 19 | LLM mock exact response? | **Defined** — fixed JSON with AAPL buy (see Section 12) |
| 20 | GitHub Actions CI in scope? | **Yes** — `.github/workflows/ci.yml` added (backend pytest + frontend build) |
| 21 | Next.js vs Vite+React simplification? | **Keep Next.js** — course explicitly teaches Next.js |
| 22 | `user_id` columns vs single-user claim? | **Keep `user_id`** — intentional forward-compatibility; noted in rationale table |
| 23 | `daily change %` — how calculated in simulator? | **% change from simulator seed price** (start-of-session baseline), not a real trading day |
