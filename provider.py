"""Transports and key routing for Jev Decision endpoints.

Routes caller keys by prefix ('sk-or-' -> OpenRouter, otherwise TypeSafe),
falling back to communal keys subject to budget.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv

# Ensure .env is loaded before server.py imports provider.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

OPENROUTER_URL = os.environ.get("OPENROUTER_URL", "https://openrouter.ai/api/alpha/decisions")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "typesafe/jev-1.13")
TYPESAFE_URL = os.environ.get("TYPESAFE_URL", "https://api.typesafe.ai/v1/systemone")
TYPESAFE_MODEL = os.environ.get("TYPESAFE_MODEL", "jev-latest")

TIMEOUT = float(os.environ.get("PROVIDER_TIMEOUT", "120"))


class Interrupted(Exception):
    """Raised on API failure; code holds HTTP status string or 'budget'."""

    def __init__(self, message: str, code: str | int | None = None):
        super().__init__(message)
        self.code = str(code) if code is not None else None


def error_code(exc: BaseException) -> str:
    """Extract standard error code string from exception."""
    code = getattr(exc, "code", None)
    if code:
        return str(code)
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.HTTPError):
        return "network"
    return "error"


@dataclass(frozen=True)
class Provider:
    """Endpoint configuration and bearer token credentials."""
    name: str
    key: str
    url: str
    model: str


def _provider(name: str, key: str, url: str, model: str) -> Provider | None:
    key = (key or "").strip()
    return Provider(name=name, key=key, url=url, model=model) if key else None


PROVIDER_OR = _provider("openrouter", os.environ.get("OPENROUTER_API_KEY", ""), OPENROUTER_URL, OPENROUTER_MODEL)
PROVIDER_TS = _provider("typesafe", os.environ.get("TYPESAFE_API_KEY", ""), TYPESAFE_URL, TYPESAFE_MODEL)


def pick_provider(own_key: str | None, budget_or, budget_ts) -> Provider:
    """Select provider based on user key or available communal budget."""
    if own_key:
        if own_key.startswith("sk-or-"):
            return Provider("openrouter", own_key, OPENROUTER_URL, OPENROUTER_MODEL)
        return Provider("typesafe", own_key, TYPESAFE_URL, TYPESAFE_MODEL)
    if PROVIDER_OR is not None and not budget_or.exhausted():
        return PROVIDER_OR
    if PROVIDER_TS is not None and not budget_ts.exhausted():
        return PROVIDER_TS
    raise Interrupted("no provider with budget left", "budget")


def _error_message(response: httpx.Response) -> str:
    """Extract truncated error message from HTTP response."""
    try:
        body = response.json()
    except ValueError:
        return (response.text or "").strip()[:200] or "no body"
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            return str(err.get("message") or err)[:200]
        if err:
            return str(err)[:200]
        if body.get("message"):
            return str(body["message"])[:200]
    return str(body)[:200]


async def post_jev(client: httpx.AsyncClient, p: Provider, state: str, questions: dict) -> dict:
    """Execute Decisions API request against selected provider."""
    body = {"model": p.model, "state": state, "questions": questions}
    headers = {"Authorization": f"Bearer {p.key}", "Content-Type": "application/json"}
    try:
        response = await client.post(p.url, headers=headers, json=body, timeout=TIMEOUT)
    except httpx.TimeoutException as e:
        raise Interrupted(f"{p.name}: timed out after {TIMEOUT:.0f}s", "timeout") from e
    except httpx.HTTPError as e:
        raise Interrupted(f"{p.name}: unreachable ({e.__class__.__name__}: {e})", "network") from e
    if response.status_code != 200:
        raise Interrupted(f"{p.name} {response.status_code}: {_error_message(response)}", response.status_code)
    try:
        data = response.json()
    except ValueError as e:
        raise Interrupted(f"{p.name}: response was not json ({response.text[:200]!r})", "bad_response") from e
    if not isinstance(data, dict) or "answers" not in data:
        raise Interrupted(f"{p.name}: response had no answers", "bad_response")
    return data
