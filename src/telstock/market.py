"""Market data layer: fetch quotes from Yahoo Finance and classify valuations.

Verdict rules (PEG ratio):
    PEG < 1   -> BARGAIN     (growth is cheap relative to earnings)
    1 <= PEG <= 4 -> FAIR
    PEG > 4   -> OVERPRICED
    no PEG    -> UNKNOWN     (P/E ratios still shown for context)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum

import yfinance as yf

from telstock import config

logger = logging.getLogger(__name__)


class Verdict(Enum):
    BARGAIN = ("🟢", "Bargain — growth is cheap at this price")
    FAIR = ("🟡", "Fairly priced")
    OVERPRICED = ("🔴", "Overpriced right now")
    UNKNOWN = ("⚪", "Not enough data for a verdict")

    @property
    def emoji(self) -> str:
        return self.value[0]

    @property
    def label(self) -> str:
        return self.value[1]


@dataclass
class Quote:
    ticker: str
    name: str
    price: float | None
    currency: str
    pe: float | None          # trailing P/E
    forward_pe: float | None
    peg: float | None
    verdict: Verdict
    fetched_at: float

    @property
    def earnings_growing(self) -> bool | None:
        """Forward P/E below trailing P/E implies the market expects earnings growth."""
        if self.pe is None or self.forward_pe is None:
            return None
        return self.forward_pe < self.pe


def classify(peg: float | None) -> Verdict:
    """Apply the PEG thresholds from config."""
    if peg is None or peg <= 0:
        return Verdict.UNKNOWN
    if peg < config.PEG_BARGAIN_MAX:
        return Verdict.BARGAIN
    if peg > config.PEG_OVERPRICED_MIN:
        return Verdict.OVERPRICED
    return Verdict.FAIR


def _num(value) -> float | None:
    """Coerce a Yahoo info field to float, treating junk as missing."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # filter NaN


# module-level quote cache: ticker -> Quote
_cache: dict[str, Quote] = {}

# dynamic watchlist cache: (built_at, {ticker: display_name})
_watchlist_cache: tuple[float, dict[str, str]] | None = None


def _short_label(name: str | None, ticker: str) -> str:
    """Compact button label from a company short name."""
    if not name:
        return ticker
    # First word is usually enough ("NVIDIA Corporation" -> "NVIDIA"); fall
    # back to the ticker for names that start generically.
    word = name.split()[0].rstrip(",")
    return word if len(word) > 2 else ticker


def get_watchlist() -> dict[str, str]:
    """Build the watchlist dynamically: pinned favorites + today's most-active
    US stocks from Yahoo's screener. Falls back to the static list offline.

    Returns {ticker: display_name} with emojis, capped at WATCHLIST_SIZE.
    """
    global _watchlist_cache
    if _watchlist_cache and time.time() - _watchlist_cache[0] < config.WATCHLIST_TTL_SECONDS:
        return _watchlist_cache[1]

    watchlist: dict[str, str] = {
        t: f"{emoji} {t}" for t, emoji in config.PINNED_TICKERS.items()
    }
    try:
        result = yf.screen(config.SCREENER, count=config.WATCHLIST_SIZE * 2)
        for q in result.get("quotes", []):
            if len(watchlist) >= config.WATCHLIST_SIZE:
                break
            ticker = q.get("symbol")
            if not ticker or ticker in watchlist or q.get("quoteType") != "EQUITY":
                continue
            emoji = config.TICKER_EMOJI.get(ticker, config.DEFAULT_EMOJI)
            watchlist[ticker] = f"{emoji} {_short_label(q.get('shortName'), ticker)}"
    except Exception:
        logger.exception("Screener failed — using fallback watchlist")
        watchlist = dict(config.FALLBACK_WATCHLIST)

    _watchlist_cache = (time.time(), watchlist)
    return watchlist


def get_quote(ticker: str, display_name: str | None = None) -> Quote:
    """Fetch a quote (cached for CACHE_TTL_SECONDS)."""
    cached = _cache.get(ticker)
    if cached and time.time() - cached.fetched_at < config.CACHE_TTL_SECONDS:
        return cached

    info = yf.Ticker(ticker).info
    peg = _num(info.get("trailingPegRatio")) or _num(info.get("pegRatio"))
    quote = Quote(
        ticker=ticker,
        name=display_name or info.get("shortName", ticker),
        price=_num(info.get("currentPrice")) or _num(info.get("regularMarketPrice")),
        currency=info.get("currency", "USD"),
        pe=_num(info.get("trailingPE")),
        forward_pe=_num(info.get("forwardPE")),
        peg=peg,
        verdict=classify(peg),
        fetched_at=time.time(),
    )
    _cache[ticker] = quote
    return quote


def get_watchlist_quotes() -> list[Quote]:
    """Fetch quotes for every ticker on the current watchlist, skipping failures."""
    quotes: list[Quote] = []
    for ticker, name in get_watchlist().items():
        try:
            quotes.append(get_quote(ticker, display_name=name))
        except Exception:
            logger.exception("Failed to fetch %s — skipping", ticker)
    return quotes
