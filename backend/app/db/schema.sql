-- FinAlly database schema

CREATE TABLE IF NOT EXISTS users_profile (
    id TEXT PRIMARY KEY DEFAULT 'default',
    cash_balance REAL NOT NULL DEFAULT 10000.0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlist (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    added_at TEXT NOT NULL,
    UNIQUE (user_id, ticker)
);

CREATE TABLE IF NOT EXISTS positions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    quantity REAL NOT NULL,
    avg_cost REAL NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (user_id, ticker)
);

CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    executed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    total_value REAL NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    actions TEXT,
    created_at TEXT NOT NULL
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_watchlist_user        ON watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_user_ticker ON watchlist(user_id, ticker);
CREATE INDEX IF NOT EXISTS idx_positions_user        ON positions(user_id);
CREATE INDEX IF NOT EXISTS idx_positions_user_ticker ON positions(user_id, ticker);
CREATE INDEX IF NOT EXISTS idx_trades_user           ON trades(user_id);
CREATE INDEX IF NOT EXISTS idx_trades_ticker         ON trades(user_id, ticker);
CREATE INDEX IF NOT EXISTS idx_snapshots_user        ON portfolio_snapshots(user_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_recorded_at ON portfolio_snapshots(recorded_at);
CREATE INDEX IF NOT EXISTS idx_chat_user             ON chat_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_created          ON chat_messages(created_at);
