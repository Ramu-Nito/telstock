"""Vercel-compatible entrypoint for the TelStock project.

This module provides a minimal WSGI application so Vercel can discover the
Python app during deployment. The Telegram bot itself still runs via polling
locally or in a long-running environment; this entrypoint is intended to keep
Vercel deployments healthy and provide a simple health check endpoint.
"""

from __future__ import annotations

from typing import Callable


def app(environ: dict[str, object], start_response: Callable[[str, list[tuple[str, str]]], None]):
    """Minimal WSGI application for Vercel."""
    path = environ.get("PATH_INFO", "/") or "/"
    if path == "/healthz":
        body = b"TelStock service is healthy."
        status = "200 OK"
    else:
        body = b"TelStock deployment ready."
        status = "200 OK"

    headers = [("Content-Type", "text/plain; charset=utf-8")]
    start_response(status, headers)
    return [body]
