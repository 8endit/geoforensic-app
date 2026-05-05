"""Redis-backed cache for Nominatim geocoding responses.

Nominatim is rate-limited (1 req/s) and externally hosted. Address lookups
rarely change — we cache them for 30 days by default. If Redis is
unreachable the cache silently turns into a no-op and the pipeline keeps
working against the live Nominatim API.

Key layout:
    geocode:v1:full:<norm>                 → tuple for geocode_address()
    geocode:v1:suggest:<country>:<norm>    → suggestion list for geocode_suggest()

Keys are lower-cased and whitespace-collapsed so trivially different spellings
("Schulstr. 2, 76571 Gaggenau" vs. "schulstr. 2,  76571  gaggenau") share a
slot.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import redis.asyncio as redis_async
from redis.exceptions import RedisError

from app.config import get_settings

logger = logging.getLogger(__name__)

_WHITESPACE_RE = re.compile(r"\s+")

_client: redis_async.Redis | None = None
_disabled: bool = False


def _normalize(s: str) -> str:
    return _WHITESPACE_RE.sub(" ", s.strip().lower())


async def _get_client() -> redis_async.Redis | None:
    global _client, _disabled
    if _disabled:
        return None
    if _client is not None:
        return _client
    url = get_settings().redis_url
    if not url:
        _disabled = True
        return None
    try:
        client = redis_async.from_url(
            url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
        )
        await client.ping()
    except (RedisError, OSError) as exc:
        logger.warning("geocode cache disabled (Redis unreachable at %s): %s", url, exc)
        _disabled = True
        return None
    _client = client
    return _client


async def cache_get(key: str) -> Any | None:
    client = await _get_client()
    if client is None:
        return None
    try:
        raw = await client.get(key)
    except (RedisError, OSError) as exc:
        logger.warning("geocode cache GET failed for %r: %s", key, exc)
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("geocode cache corrupt entry at %r — evicting", key)
        try:
            await client.delete(key)
        except (RedisError, OSError):
            pass
        return None


async def cache_set(key: str, value: Any) -> None:
    client = await _get_client()
    if client is None:
        return
    try:
        payload = json.dumps(value)
    except TypeError as exc:
        logger.warning("geocode cache SET skipped for %r (not JSON-serializable): %s", key, exc)
        return
    try:
        await client.set(key, payload, ex=get_settings().geocode_cache_ttl_seconds)
    except (RedisError, OSError) as exc:
        logger.warning("geocode cache SET failed for %r: %s", key, exc)


async def cache_delete(key: str) -> None:
    """Remove a single cache entry (used to self-heal poisoned values).

    Wenn Redis nicht erreichbar ist, log + ignorieren — der nächste Read
    läuft sonst in der gleichen vergifteten Antwort. Das Self-Heal-
    Verhalten degradiert sauber zu „kein Cache" statt zu Fehler.
    """
    client = await _get_client()
    if client is None:
        return
    try:
        await client.delete(key)
    except (RedisError, OSError) as exc:
        logger.warning("geocode cache DELETE failed for %r: %s", key, exc)


def key_full(address: str) -> str:
    return f"geocode:v1:full:{_normalize(address)}"


def key_suggest(address: str, country: str) -> str:
    return f"geocode:v1:suggest:{country.strip().lower()}:{_normalize(address)}"
