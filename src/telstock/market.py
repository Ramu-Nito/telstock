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


def get_watchlist_quotes(market: str = config.DEFAULT_MARKET) -> list[Quote]:
    """Fetch quotes for every ticker on a market's watchlist, skipping failures."""
    quotes: list[Quote] = []
    for ticker, name in config.WATCHLISTS[market].items():
        try:
            quotes.append(get_quote(ticker, display_name=name))
        except Exception:
            logger.exception("Failed to fetch %s — skipping", ticker)
    return quotes
