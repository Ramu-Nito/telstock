# 📈 TelStock

**A Telegram bot for tracking US stocks with instant valuation verdicts — big buttons, emojis, zero typing.**

TelStock puts a stock watchlist inside Telegram. Tap a button, get the price plus a traffic-light valuation verdict computed from three numbers: **P/E**, **Forward P/E**, and the **PEG ratio**.

| Verdict | Rule | Meaning |
|---|---|---|
| 🟢 Bargain | PEG < 1 | Growth is cheap at this price |
| 🟡 Fair | 1 ≤ PEG ≤ 4 | Reasonably priced |
| 🔴 Overpriced | PEG > 4 | Too expensive right now |
| ⚪ Unknown | no PEG data | P/E ratios still shown for context |

## The interface

```
🏠 Main menu
├── 💰 Check Stock Price   → tap a company → full stock card (price, P/E,
│                            Forward P/E, PEG, verdict) with 🔄 Refresh
├── 🔥 Bargains Now        → watchlist stocks with PEG < 1
├── 💸 Overpriced Now      → watchlist stocks with PEG > 4
└── 📊 Watchlist Overview  → every stock, one line each, with 🟢🟡🔴 dots
```

The bot **edits messages in place** instead of spamming the chat — navigating feels like using an app with screens, not texting a robot.

**The watchlist builds itself.** Pinned favorites (🚀 SpaceX, 🎮 Nvidia, 🪟 Microsoft, 🔧 AMD) always come first; the rest of the grid is filled with **today's most active US stocks** from Yahoo's screener, refreshed every 15 minutes. Open the bot on a different day, see different movers.

Data comes from Yahoo Finance (free, no API key) with a 5-minute quote cache. Bonus signal on every stock card: if Forward P/E is below trailing P/E, the market expects earnings to grow 📈.

## Setup

### 1. Create your bot with BotFather

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot`, pick a display name (e.g. *TelStock*) and a unique username (must end in `bot`, e.g. `my_telstock_bot`)
3. BotFather replies with a **token** like `123456789:AAF...` — copy it

### 2. Install and run

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
pip install -e .
```

```powershell
$env:TELEGRAM_BOT_TOKEN = "123456789:AAF-your-token-here"
python -m telstock.bot
```

Open your bot in Telegram, send `/start`, and tap away.

## Project layout

```
telstock/
├── src/telstock/
│   ├── config.py    # watchlist, PEG thresholds, cache TTL
│   ├── market.py    # Yahoo Finance quotes + valuation classifier
│   └── bot.py       # Telegram handlers, keyboards, message formatting
├── tests/           # pytest suite (logic tested without network or token)
└── .github/workflows/ci.yml
```

## Extending

- **Pin a favorite:** one line in `config.PINNED_TICKERS` — emoji included
- **Change the dynamic source:** swap `config.SCREENER` for any yfinance predefined screener (`day_gainers`, `day_losers`, `growth_technology_stocks`, ...)
- **Tune the thresholds:** `PEG_BARGAIN_MAX` / `PEG_OVERPRICED_MIN` in `config.py`

## Tech stack

Python · python-telegram-bot · yfinance · pytest · GitHub Actions

> ⚠️ TelStock is a hobby tool, not financial advice. PEG-based rules are a rough heuristic — always do your own research.
