import asyncio
import time
from types import SimpleNamespace

from telstock import bot
from telstock.market import Quote, Verdict


def _quote(ticker="NVDA", verdict=Verdict.BARGAIN, peg=0.8) -> Quote:
    return Quote(
        ticker=ticker,
        name=f"🎮 {ticker}",
        price=123.45,
        currency="USD",
        pe=40.0,
        forward_pe=30.0,
        peg=peg,
        verdict=verdict,
        fetched_at=time.time(),
    )


def test_main_menu_has_search_action():
    kb = bot.main_menu_keyboard().inline_keyboard
    callbacks = [btn.callback_data for row in kb for btn in row]
    assert callbacks == [
        "menu:prices",
        "menu:bargains",
        "menu:overpriced",
        "menu:overview",
        "menu:search",
    ]


def test_ticker_keyboard_covers_watchlist_plus_back():
    watchlist = {"SPCX": "🚀 SPCX", "NVDA": "🎮 NVDA", "WULF": "💹 TeraWulf"}
    kb = bot.ticker_keyboard(watchlist).inline_keyboard
    callbacks = [btn.callback_data for row in kb for btn in row]
    tickers = [c.split(":")[1] for c in callbacks if c.startswith("stock:")]
    assert tickers == list(watchlist.keys())
    assert callbacks[-1] == "menu:main"


def test_stock_card_contains_key_numbers():
    text = bot.format_stock_card(_quote())
    assert "123.45" in text
    assert "40.00" in text  # P/E
    assert "0.80" in text   # PEG
    assert Verdict.BARGAIN.emoji in text
    assert "expects earnings to grow" in text


def test_stock_card_handles_missing_data():
    q = _quote(verdict=Verdict.UNKNOWN, peg=None)
    q.pe = None
    q.forward_pe = None
    q.price = None
    text = bot.format_stock_card(q)
    assert "—" in text
    assert Verdict.UNKNOWN.emoji in text


def test_scan_filters_by_verdict():
    quotes = [
        _quote("CHEAP", Verdict.BARGAIN, peg=0.5),
        _quote("MEH", Verdict.FAIR, peg=2.0),
        _quote("RICH", Verdict.OVERPRICED, peg=6.0),
    ]
    bargains = bot.format_scan(quotes, Verdict.BARGAIN, "none")
    assert "CHEAP" in bargains and "RICH" not in bargains

    pricey = bot.format_scan(quotes, Verdict.OVERPRICED, "none")
    assert "RICH" in pricey and "CHEAP" not in pricey


def test_scan_empty_message():
    assert bot.format_scan([], Verdict.BARGAIN, "no bargains") == "no bargains"


def test_build_application_creates_bot_app():
    app = bot.build_application("dummy-token")
    assert app is not None


def test_process_ticker_lookup_fetches_quote_for_valid_input():
    class DummyMessage:
        def __init__(self, text: str):
            self.text = text
            self.replies: list[tuple[str, dict]] = []

        async def reply_text(self, text: str, **kwargs):
            self.replies.append((text, kwargs))

    class DummyUpdate:
        def __init__(self, text: str):
            self.message = DummyMessage(text)

    update = DummyUpdate("nvda")
    context = SimpleNamespace(user_data={})
    quote = _quote("NVDA")

    def fake_watchlist():
        return {"NVDA": "🎮 NVDA"}

    def fake_quote(ticker: str, display_name: str | None = None):
        assert ticker == "NVDA"
        assert display_name == "🎮 NVDA"
        return quote

    asyncio.run(
        bot.process_ticker_lookup(
            update,
            context,
            watchlist_fetcher=fake_watchlist,
            quote_fetcher=fake_quote,
        )
    )

    assert update.message.replies[0][0] == "⏳ Fetching <b>NVDA</b>..."
    assert update.message.replies[1][0] == bot.format_stock_card(quote)
