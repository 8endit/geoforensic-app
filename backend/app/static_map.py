"""Static map fetcher for the teaser PDF header.

Produces a small OSM-backed snippet with a red pin on the address, used on
page 1 of the teaser. We render via matplotlib + contextily against CartoDB
Positron tiles — the same provider that backs the points-map on page 2 —
because the previous community host (staticmap.openstreetmap.de) regularly
returned "service unavailable" placeholder PNGs at peak times.

Network / tile failures return an empty string. The template then falls back
to a grey coord-labelled placeholder so a flaky tile service never blocks
PDF generation.
"""

import asyncio
import logging

from app.pointmap import render_address_pin

logger = logging.getLogger(__name__)


async def fetch_static_map(
    lat: float,
    lon: float,
    width: int = 400,
    height: int = 250,
    zoom: int = 16,
) -> str:
    """Return ``data:image/png;base64,...`` or empty string on failure.

    ``width`` / ``height`` / ``zoom`` are kept for API compatibility with the
    previous implementation; the matplotlib renderer scales via inch-based
    figsize instead, so only the aspect ratio matters.
    """
    try:
        data_uri = await asyncio.to_thread(render_address_pin, lat, lon)
    except Exception as exc:
        logger.warning("address pin render raised: %s: %s", type(exc).__name__, exc)
        return ""
    if data_uri:
        logger.info("Static map rendered for (%s, %s)", lat, lon)
    else:
        logger.warning("Static map rendering returned empty for (%s, %s) — fallback will be shown", lat, lon)
    return data_uri
