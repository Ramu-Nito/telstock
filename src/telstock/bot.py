"""TelStock Telegram bot: button-driven stock tracking.

Run with:  python -m telstock.bot
Requires TELEGRAM_BOT_TOKEN in the environment (token from @BotFather).
"""

from __future__ import annotations

import asyncio
import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from telstock import config, market
from telstock.market import Quote, Verdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("telstock.bot")


# ---------- keyboards ----------

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💰 Check Stock Price", callback_data="menu:prices")],
            [
                InlineKeyboardButton("🔥 Bargains Now", callback_data="menu:bargains"),
                InlineKeyboardButton("💸 Overpriced Now", callback_data="menu:overpriced"),
            ],
            [InlineKeyboardButton("📊 Watchlist Overview", callback_data="menu:overview")],
        ]
    )


def ticker_keyboard(watchlist: dict[str, str]) -> InlineKeyboardMarkup:
    """Grid of watchlist tickers, two per row, plus a back button."""
    buttons = [
        InlineKeyboardButton(name, callback_data=f"stock:{ticker}")
        for ticker, name in watchlist.items()
    ]
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


def stock_keyboard(ticker: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"stock:{ticker}"),
                InlineKeyboardButton("⬅️ Back", callback_data="menu:prices"),
            ],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="menu:main")],
        ]
    )


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 Main Menu", callback_data="menu:main")]]
    )


# ---------- message formatting ----------

def _fmt(value: float | None, suffix: str = "") -> str:
    return f"{value:,.2f}{suffix}" if value is not None else "—"


def format_stock_card(q: Quote) -> str:
    growth = ""
    if q.earnings_growing is True:
        growth = "\n📈 Forward P/E below trailing — market expects earnings to grow"
    elif q.earnings_growing is False:
        growth = "\n📉 Forward P/E above trailing — market expects earnings to shrink"

    return (
        f"<b>{q.name}</b>  (<code>{q.ticker}</code>)\n\n"
        f"💵 Price: <b>{_fmt(q.price)} {q.currency}</b>\n"
        f"➗ P/E: <b>{_fmt(q.pe)}</b>\n"
        f"⏭️ Forward P/E: <b>{_fmt(q.forward_pe)}</b>\n"
        f"⚖️ PEG: <b>{_fmt(q.peg)}</b>\n\n"
        f"{q.verdict.emoji} <b>{q.verdict.label}</b>{growth}"
    )


def format_quote_line(q: Quote) -> str:
    return (
        f"{q.verdict.emoji} <b>{q.ticker}</b> {_fmt(q.price)} {q.currency}"
        f"  ·  PEG {_fmt(q.peg)}"
    )


def format_scan(quotes: list[Quote], verdict: Verdict, empty_text: str) -> str:
    hits = [q for q in quotes if q.verdict is verdict]
    if not hits:
        return empty_text
    return "\n".join(format_quote_line(q) for q in sorted(hits, key=lambda q: q.peg or 0))


# ---------- handlers ----------

WELCOME = (
    "👋 <b>Welcome to TelStock!</b>\n\n"
    "Track today's most active US stocks (NYSE + NASDAQ) — the watchlist "
    "updates itself with what the market is trading right now. Instant "
    "valuation verdicts based on PEG ratio:\n"
    f"🟢 bargain (PEG &lt; {config.PEG_BARGAIN_MAX:g})  ·  "
    f"🟡 fair  ·  "
    f"🔴 overpriced (PEG &gt; {config.PEG_OVERPRICED_MIN:g})\n\n"
    "What would you like to do?"
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        WELCOME, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML
    )


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "menu:main":
        await query.edit_message_text(
            WELCOME, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML
        )

    elif action == "menu:prices":
        await query.edit_message_text("⏳ Loading today's movers...", parse_mode=ParseMode.HTML)
        watchlist = await asyncio.to_thread(market.get_watchlist)
        await query.edit_message_text(
            "💰 <b>Pick a stock</b> (pinned favorites + today's most active):",
            reply_markup=ticker_keyboard(watchlist),
            parse_mode=ParseMode.HTML,
        )

    elif action.startswith("stock:"):
        ticker = action.split(":", 1)[1]
        await query.edit_message_text(f"⏳ Fetching <b>{ticker}</b>...", parse_mode=ParseMode.HTML)
        watchlist = await asyncio.to_thread(market.get_watchlist)
        quote = await asyncio.to_thread(market.get_quote, ticker, watchlist.get(ticker))
        await query.edit_message_text(
            format_stock_card(quote),
            reply_markup=stock_keyboard(ticker),
            parse_mode=ParseMode.HTML,
        )

    elif action in ("menu:bargains", "menu:overpriced", "menu:overview"):
        await query.edit_message_text("⏳ Scanning the watchlist...", parse_mode=ParseMode.HTML)
        quotes = await asyncio.to_thread(market.get_watchlist_quotes)

        if action == "menu:bargains":
            body = format_scan(
                quotes, Verdict.BARGAIN,
                "😕 No bargains on the watchlist right now. Check back later!",
            )
            text = f"🔥 <b>Bargains right now</b> (PEG &lt; {config.PEG_BARGAIN_MAX:g})\n\n{body}"
        elif action == "menu:overpriced":
            body = format_scan(
                quotes, Verdict.OVERPRICED,
                "🎉 Nothing on the watchlist looks overpriced right now.",
            )
            text = f"💸 <b>Overpriced right now</b> (PEG &gt; {config.PEG_OVERPRICED_MIN:g})\n\n{body}"
        else:
            lines = [format_quote_line(q) for q in quotes]
            text = "📊 <b>Watchlist overview</b>\n\n" + "\n".join(lines)

        await query.edit_message_text(
            text, reply_markup=back_keyboard(), parse_mode=ParseMode.HTML
        )


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN is not set.\n"
            "Create a bot with @BotFather on Telegram, then:\n"
            '  PowerShell:  $env:TELEGRAM_BOT_TOKEN = "123456:ABC-your-token"'
        )
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_button))
    logger.info("TelStock is running — press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
