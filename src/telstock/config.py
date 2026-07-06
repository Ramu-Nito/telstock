"""TelStock configuration: watchlist, valuation thresholds, cache settings."""

# US markets (NYSE + NASDAQ). Structured per-market so more exchanges can be
# added later without touching the bot logic.
WATCHLISTS: dict[str, dict[str, str]] = {
    "US": {
        "NVDA": "🎮 Nvidia",
        "AMD": "🔧 AMD",
        "MSFT": "🪟 Microsoft",
        "AAPL": "🍎 Apple",
        "GOOGL": "🔍 Alphabet",
        "AMZN": "📦 Amazon",
        "META": "👥 Meta",
        "TSLA": "🚗 Tesla",
        "JPM": "🏦 JPMorgan",
        "KO": "🥤 Coca-Cola",
        "DIS": "🏰 Disney",
        "NFLX": "🎬 Netflix",
    },
}

DEFAULT_MARKET = "US"

# Valuation verdict thresholds (PEG ratio).
PEG_BARGAIN_MAX = 1.0   # PEG under 1 → good deal
PEG_OVERPRICED_MIN = 4.0  # PEG over 4 → too expensive

# How long fetched quotes stay fresh before re-fetching (seconds).
CACHE_TTL_SECONDS = 300
