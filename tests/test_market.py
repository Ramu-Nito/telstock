import time

import pytest

from telstock import market
from telstock.market import Quote, Verdict, classify


@pytest.mark.parametrize(
    ("peg", "expected"),
    [
        (0.5, Verdict.BARGAIN),
        (0.99, Verdict.BARGAIN),
        (1.0, Verdict.FAIR),
        (2.5, Verdict.FAIR),
        (4.0, Verdict.FAIR),
        (4.01, Verdict.OVERPRICED),
        (12.0, Verdict.OVERPRICED),
        (None, Verdict.UNKNOWN),
        (0.0, Verdict.UNKNOWN),
        (-1.5, Verdict.UNKNOWN),
    ],
)
def test_classify_thresholds(peg, expected):
    assert classify(peg) is expected


def test_num_handles_junk():
    assert market._num("31.5") == 31.5
    assert market._num(None) is None
    assert market._num("Infinity") is not None  # inf is a float; NaN is not
    assert market._num(float("nan")) is None
    assert market._num("abc") is None


def _quote(**overrides) -> Quote:
    base = dict(
        ticker="TEST",
        name="Test Corp",
        price=100.0,
        currency="USD",
        pe=30.0,
        forward_pe=25.0,
        peg=1.5,
        verdict=Verdict.FAIR,
        fetched_at=time.time(),
    )
    base.update(overrides)
    return Quote(**base)


def test_earnings_growing_when_forward_pe_lower():
    assert _quote(pe=30.0, forward_pe=25.0).earnings_growing is True
    assert _quote(pe=20.0, forward_pe=28.0).earnings_growing is False
    assert _quote(pe=None, forward_pe=25.0).earnings_growing is None


def test_watchlist_pins_first_then_screener(monkeypatch):
    def fake_screen(name, count=None):
        return {
            "quotes": [
                {"symbol": "NVDA", "shortName": "NVIDIA Corporation", "quoteType": "EQUITY"},  # dupe of pin
                {"symbol": "WULF", "shortName": "TeraWulf Inc.", "quoteType": "EQUITY"},
                {"symbol": "BTC-USD", "shortName": "Bitcoin", "quoteType": "CRYPTOCURRENCY"},  # filtered
                {"symbol": "INTC", "shortName": "Intel Corporation", "quoteType": "EQUITY"},
            ]
        }

    monkeypatch.setattr(market.yf, "screen", fake_screen)
    market._watchlist_cache = None

    wl = market.get_watchlist()
    tickers = list(wl)
    # pins come first, in config order
    assert tickers[: len(market.config.PINNED_TICKERS)] == list(market.config.PINNED_TICKERS)
    # screener equities appended, non-equities filtered, no duplicates
    assert "WULF" in wl and "INTC" in wl
    assert "BTC-USD" not in wl
    assert tickers.count("NVDA") == 1


def test_watchlist_falls_back_when_screener_dies(monkeypatch):
    def broken_screen(name, count=None):
        raise ConnectionError("yahoo is down")

    monkeypatch.setattr(market.yf, "screen", broken_screen)
    market._watchlist_cache = None

    wl = market.get_watchlist()
    assert wl == market.config.FALLBACK_WATCHLIST


def test_get_quote_uses_cache(monkeypatch):
    calls = []

    class FakeTicker:
        def __init__(self, symbol):
            calls.append(symbol)
            self.info = {
                "shortName": "Fake Corp",
                "currentPrice": 50.0,
                "currency": "USD",
                "trailingPE": 20.0,
                "forwardPE": 18.0,
                "trailingPegRatio": 0.8,
            }

    monkeypatch.setattr(market.yf, "Ticker", FakeTicker)
    market._cache.clear()

    q1 = market.get_quote("FAKE")
    q2 = market.get_quote("FAKE")  # served from cache
    assert calls == ["FAKE"]
    assert q1 is q2
    assert q1.verdict is Verdict.BARGAIN
    assert q1.price == 50.0
