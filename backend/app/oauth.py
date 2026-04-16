"""OAuth ID-token verification for Google and Apple Sign-In."""

import logging
from typing import Any

import httpx
import jwt as pyjwt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ── Apple JWKS cache ────────────────────────────────────────────────
_apple_jwks: list[dict[str, Any]] = []

APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"


async def _fetch_apple_jwks() -> list[dict[str, Any]]:
    """Fetch Apple's public keys (JWKS). Cached in-memory, refreshed on miss."""
    global _apple_jwks  # noqa: PLW0603
    if _apple_jwks:
        return _apple_jwks
    async with httpx.AsyncClient() as client:
        resp = await client.get(APPLE_JWKS_URL, timeout=10.0)
        resp.raise_for_status()
        _apple_jwks = resp.json()["keys"]
    return _apple_jwks


async def _get_apple_public_key(kid: str) -> pyjwt.algorithms.RSAAlgorithm:
    """Find the Apple public key matching the given key ID."""
    keys = await _fetch_apple_jwks()
    for key in keys:
        if key["kid"] == kid:
            return pyjwt.algorithms.RSAAlgorithm.from_jwk(key)

    # Key not found — try refreshing the cache once
    global _apple_jwks  # noqa: PLW0603
    _apple_jwks = []
    keys = await _fetch_apple_jwks()
    for key in keys:
        if key["kid"] == kid:
            return pyjwt.algorithms.RSAAlgorithm.from_jwk(key)
    raise ValueError(f"Apple public key with kid={kid!r} not found")


# ── Public API ──────────────────────────────────────────────────────


def verify_google_token(token: str) -> dict[str, str]:
    """Verify a Google ID token and return user info.

    Returns dict with keys: email, sub, name (optional).
    Raises ValueError on invalid/expired token.
    """
    if not settings.google_client_id:
        raise ValueError("Google OAuth not configured (GOOGLE_CLIENT_ID missing)")

    try:
        info = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.google_client_id,
        )
    except Exception as exc:
        raise ValueError(f"Invalid Google ID token: {exc}") from exc

    email = info.get("email")
    if not email or not info.get("email_verified"):
        raise ValueError("Google account email not verified")

    return {
        "email": email.lower(),
        "sub": info["sub"],
        "name": info.get("name"),
    }


async def verify_apple_token(token: str) -> dict[str, str]:
    """Verify an Apple ID token and return user info.

    Returns dict with keys: email, sub.
    Raises ValueError on invalid/expired token.
    """
    if not settings.apple_client_id:
        raise ValueError("Apple OAuth not configured (APPLE_CLIENT_ID missing)")

    try:
        unverified_header = pyjwt.get_unverified_header(token)
        kid = unverified_header["kid"]
        public_key = await _get_apple_public_key(kid)
        claims = pyjwt.decode(
            token,
            key=public_key,
            algorithms=["RS256"],
            audience=settings.apple_client_id,
            issuer=APPLE_ISSUER,
        )
    except Exception as exc:
        raise ValueError(f"Invalid Apple ID token: {exc}") from exc

    email = claims.get("email")
    if not email:
        raise ValueError("Apple token missing email claim")

    return {
        "email": email.lower(),
        "sub": claims["sub"],
    }
