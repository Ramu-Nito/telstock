"""TelStock configuration: dynamic watchlist settings, valuation thresholds, cache."""

# ---- Dynamic watchlist -----------------------------------------------------
# The watchlist is built at runtime from Yahoo's "most actives" screener, so
# the buttons follow what the market is actually trading today. Pinned tickers
# are always shown first; the screener fills the remaining slots.

SCREENER = "most_actives"     # a yfinance predefined screener (US markets)
WATCHLIST_SIZE = 12           # total buttons shown
WATCHLIST_TTL_SECONDS = 900   # rebuild the dynamic list every 15 minutes

# Always-present favorites (ticker -> emoji). Order is preserved.
PINNED_TICKERS: dict[str, str] = {
    "SPCX": "🚀",
    "NVDA": "🎮",
    "MSFT": "🪟",
    "AMD": "🔧",
}

# Emojis for other well-known tickers when they show up in the screener.
TICKER_EMOJI: dict[str, str] = {
    "AAPL": "🍎", "GOOGL": "🔍", "GOOG": "🔍", "AMZN": "📦", "META": "👥",
    "TSLA": "🚗", "JPM": "🏦", "KO": "🥤", "DIS": "🏰", "NFLX": "🎬",
    "INTC": "💾", "PFE": "💊", "T": "📞", "AAL": "✈️", "F": "🛻",
    "SOFI": "💳", "NOK": "📱", "PLTR": "🛰️", "BAC": "🏦", "XOM": "🛢️",
}
DEFAULT_EMOJI = "💹"

# Fallback list used only if the screener is unreachable.
FALLBACK_WATCHLIST: dict[str, str] = {
    "SPCX": "🚀 SpaceX",
    "NVDA": "🎮 Nvidia",
    "MSFT": "🪟 Microsoft",
    "AMD": "🔧 AMD",
    "AAPL": "🍎 Apple",
    "GOOGL": "🔍 Alphabet",
    "AMZN": "📦 Amazon",
    "META": "👥 Meta",
    "TSLA": "🚗 Tesla",
    "JPM": "🏦 JPMorgan",
    "KO": "🥤 Coca-Cola",
    "NFLX": "🎬 Netflix",
}

# ---- Valuation verdict thresholds (PEG ratio) --------------------------------
PEG_BARGAIN_MAX = 1.0     # PEG under 1 -> good deal
PEG_OVERPRICED_MIN = 4.0  # PEG over 4 -> too expensive

# How long fetched quotes stay fresh before re-fetching (seconds).
CACHE_TTL_SECONDS = 300
