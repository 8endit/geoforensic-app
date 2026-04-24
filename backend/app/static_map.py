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
    """Return ``data:image/png;base64,...`` or empty string on failure.

    Every outcome is logged at INFO/WARNING so an operator tailing the
    backend container can tell at a glance whether the external
    staticmap service is up, rate-limiting, or returning placeholder
    "service unavailable" PNGs. The empty-string return path is what
    the report template keys off of for the grey coord-fallback block.
    """
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
            content_len = len(resp.content) if resp.content else 0
            if content_len < 500:
                # The service answered with 200 but the body is too small to
                # be a real map (Gravitystorm tends to send a ~200-byte
                # "service unavailable" PNG at peak times). Log this loud
                # enough that the operator notices — without this line the
                # failure was completely silent.
                logger.warning(
                    "Static map service returned %d bytes for (%s, %s) "
                    "status=%s — treating as soft failure, grey fallback "
                    "will be used in the PDF.",
                    content_len, lat, lon, resp.status_code,
                )
                return ""
            logger.info(
                "Static map fetched: %d bytes for (%s, %s)",
                content_len, lat, lon,
            )
            return "data:image/png;base64," + base64.b64encode(resp.content).decode("ascii")
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Static map HTTP %s for (%s, %s): %s",
            exc.response.status_code, lat, lon, exc,
        )
        return ""
    except httpx.TimeoutException:
        logger.warning(
            "Static map timeout (5s) for (%s, %s) — service too slow or unreachable.",
            lat, lon,
        )
        return ""
    except Exception as exc:
        logger.warning(
            "Static map fetch failed for (%s, %s): %s: %s",
            lat, lon, type(exc).__name__, exc,
        )
        return ""
