"""Webhook entrypoint for Vercel deployments of the Telegram bot."""

from __future__ import annotations

import asyncio
import logging
import os

from flask import Flask, Response, request
from telegram import Update

from telstock.bot import build_application

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telstock.webhook")

app = Flask(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
application = None
if TOKEN:
    application = build_application(TOKEN)
    application.initialize()
    if WEBHOOK_URL:
        try:
            asyncio.run(application.bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True))
            logger.info("Telegram webhook registered at %s", WEBHOOK_URL)
        except Exception as exc:
            logger.warning("Could not register Telegram webhook: %s", exc)


@app.route("/healthz", methods=["GET"])
def healthz() -> Response:
    return Response("ok", mimetype="text/plain")


@app.route("/", methods=["POST"])
@app.route("/api/webhook", methods=["POST"])
def webhook() -> Response:
    if not application:
        return Response("Telegram bot token not configured", status=500, mimetype="text/plain")

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return Response("invalid payload", status=400, mimetype="text/plain")

    update = Update.de_json(payload, application.bot)
    if update is None:
        return Response("invalid telegram update", status=400, mimetype="text/plain")

    try:
        asyncio.run(application.process_update(update))
    except Exception:
        return Response("failed to process update", status=500, mimetype="text/plain")

    return Response("ok", mimetype="text/plain")
