"""LLM integration — calls Anthropic API directly via urllib3 (no litellm needed)."""

from __future__ import annotations

import json
import logging
import os

from pydantic import BaseModel

logger = logging.getLogger(__name__)

MODEL = "claude-3-5-haiku-20241022"
TIMEOUT = 30  # seconds
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"

_MOCK_RESPONSE = {
    "message": "I've bought 5 shares of AAPL for you.",
    "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 5}],
    "watchlist_changes": [],
}

_SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant embedded in a simulated trading workstation.
You have access to the user's portfolio, cash balance, and watchlist with live prices.

Rules:
- Always respond with valid JSON matching the schema exactly — no markdown, no code fences.
- Be concise and data-driven. Reference specific numbers from the portfolio context.
- Only execute trades when the user explicitly asks or clearly agrees.
- If a trade would fail (insufficient cash or shares), explain why in the message field.

Response schema (always include all three keys):
{"message": "...", "trades": [...], "watchlist_changes": [...]}

Trade object: {"ticker": "AAPL", "side": "buy", "quantity": 10}
Watchlist change: {"ticker": "PYPL", "action": "add"}"""


class TradeAction(BaseModel):
    ticker: str
    side: str
    quantity: float


class WatchlistChange(BaseModel):
    ticker: str
    action: str


class LLMResponse(BaseModel):
    message: str
    trades: list[TradeAction] = []
    watchlist_changes: list[WatchlistChange] = []


_ERROR_RESPONSE = LLMResponse(
    message="I'm having trouble connecting right now. Please try again.",
    trades=[],
    watchlist_changes=[],
)


def _call_anthropic_sync(messages: list[dict], system: str) -> LLMResponse:
    """Synchronous HTTP call to Anthropic API using urllib3."""
    import urllib3

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return _ERROR_RESPONSE

    http = urllib3.PoolManager(
        timeout=urllib3.Timeout(connect=10, read=TIMEOUT),
        cert_reqs="CERT_REQUIRED",
    )

    payload = {
        "model": MODEL,
        "max_tokens": 1024,
        "system": system,
        "messages": messages,
    }

    try:
        resp = http.request(
            "POST",
            ANTHROPIC_API_URL,
            body=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": ANTHROPIC_API_VERSION,
            },
        )
        if resp.status != 200:
            logger.error("Anthropic API error %d: %s", resp.status, resp.data[:200])
            return _ERROR_RESPONSE

        data = json.loads(resp.data)
        raw = data["content"][0]["text"]
        # Strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return LLMResponse.model_validate_json(raw)

    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return _ERROR_RESPONSE


async def call_llm(messages: list[dict], portfolio_context: str) -> LLMResponse:
    """Call the LLM. Runs sync HTTP in a thread to avoid blocking the event loop."""
    import asyncio

    if os.environ.get("LLM_MOCK", "false").lower() == "true":
        return LLMResponse(**_MOCK_RESPONSE)

    system = f"{_SYSTEM_PROMPT}\n\nCurrent portfolio:\n{portfolio_context}"
    return await asyncio.to_thread(_call_anthropic_sync, messages, system)


def build_portfolio_context(portfolio: dict, watchlist: list[dict]) -> str:
    lines = [
        f"Cash: ${portfolio['cash_balance']:.2f}",
        f"Total value: ${portfolio['total_value']:.2f}",
        "",
        "Positions:",
    ]
    if portfolio["positions"]:
        for p in portfolio["positions"]:
            lines.append(
                f"  {p['ticker']}: {p['quantity']} shares @ ${p['avg_cost']:.2f} avg, "
                f"now ${p['current_price']:.2f}, P&L ${p['unrealized_pnl']:.2f} ({p['pnl_percent']:.1f}%)"
            )
    else:
        lines.append("  (no positions)")

    lines += ["", "Watchlist (live prices):"]
    for w in watchlist:
        price_str = f"${w['price']:.2f}" if w.get("price") else "N/A"
        lines.append(f"  {w['ticker']}: {price_str}")

    return "\n".join(lines)
