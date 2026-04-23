"""Static map fetcher for the teaser PDF (fix-list item 10).

Fetches a small OSM static map centered on the report address and returns it
as a base64 data URI so the image is embedded inline in the PDF (Chrome
Headless renders from a temp file and cannot load external URLs reliably).

Network failures — rate limit, DNS blip, timeout — return an empty string.
The caller is expected to render a grey placeholder in that case, so a
flaky map provider never breaks PDF generation.
"""

import base64
import logging

import httpx

logger = logging.getLogger(__name__)

# staticmap.openstreetmap.de is the long-running community-hosted static map
# service (Gravitystorm / Mapnik). Free, no API key, rate-limited per IP.
# If we outgrow it we swap in a paid MapTiler/Mapbox call here and nothing
# else changes.
STATIC_MAP_URL = "https://staticmap.openstreetmap.de/staticmap.php"
STATIC_MAP_USER_AGENT = "Bodenbericht/1.0 (kontakt@geoforensic.de)"


async def fetch_static_map(
    lat: float,
    lon: float,
    width: int = 400,
    height: int = 250,
    zoom: int = 16,
) -> str:
    """Return ``data:image/png;base64,...`` or empty string on failure."""
    params = {
        "center": f"{lat},{lon}",
        "zoom": zoom,
        "size": f"{width}x{height}",
        "markers": f"{lat},{lon},red-pushpin",
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                STATIC_MAP_URL,
                params=params,
                headers={"User-Agent": STATIC_MAP_USER_AGENT},
            )
            resp.raise_for_status()
            if not resp.content or len(resp.content) < 500:
                # Defensive: service sometimes returns a 200 with a tiny
                # "service unavailable" PNG. Treat that as failure.
                return ""
            return "data:image/png;base64," + base64.b64encode(resp.content).decode("ascii")
    except Exception as exc:
        logger.warning("Static map fetch failed for (%s, %s): %s", lat, lon, exc)
        return ""
