"""Static map for the teaser PDF header.

Renders a small OSM-tile map centered on the report address with a red pin
marker, returned as a base64 data URI so it embeds inline in the HTML that
becomes the PDF (Chrome Headless cannot reliably load external URLs).

Implementation: fetch a 2x2 tile mosaic from the public OSM tile server,
stitch with Pillow, draw a centered pin marker. No external static-map
service involved — the previous community host (staticmap.openstreetmap.de)
returned "service unavailable" placeholders during peak hours and was
the visible cause of the "Karte derzeit nicht verfügbar"-fallback in
the teaser.

OSM tile usage policy compliance:
- Identifying User-Agent (kontakt@geoforensic.de)
- Low volume (one map per lead, not high-frequency)
- Any failure (network, HTTP, timeout) returns empty string and the
  caller falls back to a grey coord-labelled placeholder.
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import math

import httpx

logger = logging.getLogger(__name__)

TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
USER_AGENT = "Bodenbericht/1.0 (kontakt@geoforensic.de)"
TILE_SIZE = 256


def _deg2tile(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    """Convert lat/lon to fractional tile coordinates (slippy map math)."""
    lat_rad = math.radians(lat)
    n = 2.0**zoom
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n
    return x, y


async def _fetch_tile(client: httpx.AsyncClient, z: int, x: int, y: int) -> bytes | None:
    """Fetch one OSM tile. Returns PNG bytes or None on failure."""
    try:
        resp = await client.get(
            TILE_URL.format(z=z, x=x, y=y),
            headers={"User-Agent": USER_AGENT},
            timeout=4.0,
        )
        resp.raise_for_status()
        if len(resp.content) < 200:
            return None
        return resp.content
    except (httpx.HTTPError, httpx.TimeoutException):
        return None


def _stitch_and_pin(
    tiles: list[tuple[int, int, bytes]],
    center_x_frac: float,
    center_y_frac: float,
    tile_x_min: int,
    tile_y_min: int,
    out_width: int,
    out_height: int,
) -> bytes | None:
    """Stitch tiles with Pillow, crop to centered window, draw pin. Sync."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        logger.warning("Pillow not available — cannot render static map")
        return None

    # Stitch all tiles into one canvas
    n_x = max(x for x, _, _ in tiles) - tile_x_min + 1
    n_y = max(y for _, y, _ in tiles) - tile_y_min + 1
    canvas = Image.new("RGB", (n_x * TILE_SIZE, n_y * TILE_SIZE), (240, 240, 240))
    for x, y, png in tiles:
        try:
            tile_img = Image.open(io.BytesIO(png)).convert("RGB")
            canvas.paste(tile_img, ((x - tile_x_min) * TILE_SIZE, (y - tile_y_min) * TILE_SIZE))
        except Exception:
            continue

    # Compute pixel coordinates of the address within the stitched canvas
    px = (center_x_frac - tile_x_min) * TILE_SIZE
    py = (center_y_frac - tile_y_min) * TILE_SIZE

    # Crop a window of out_width × out_height centered on (px, py)
    left = int(px - out_width / 2)
    top = int(py - out_height / 2)
    # Clamp so we never crop outside the canvas
    left = max(0, min(left, canvas.width - out_width))
    top = max(0, min(top, canvas.height - out_height))
    cropped = canvas.crop((left, top, left + out_width, top + out_height))

    # Pin position relative to crop window
    pin_x = int(px - left)
    pin_y = int(py - top)

    draw = ImageDraw.Draw(cropped)
    # Pin shadow (dark ellipse offset down-right)
    draw.ellipse(
        (pin_x - 8, pin_y - 8, pin_x + 8, pin_y + 8),
        fill=(220, 53, 69),
        outline=(255, 255, 255),
        width=2,
    )
    # Inner dot
    draw.ellipse(
        (pin_x - 3, pin_y - 3, pin_x + 3, pin_y + 3),
        fill=(255, 255, 255),
    )

    out = io.BytesIO()
    cropped.save(out, format="PNG", optimize=True)
    return out.getvalue()


async def fetch_static_map(
    lat: float,
    lon: float,
    width: int = 400,
    height: int = 250,
    zoom: int = 15,
) -> str:
    """Return ``data:image/png;base64,...`` or empty string on failure.

    Fetches a 2×2 OSM tile mosaic centered on (lat, lon), stitches with
    Pillow, draws a red pin, returns as base64 data URI for inline PDF
    embedding. Empty string return triggers the grey coord-fallback in
    the teaser template.
    """
    # Center tile coordinates (fractional)
    cx, cy = _deg2tile(lat, lon, zoom)
    tile_x = int(cx)
    tile_y = int(cy)

    # We need 2×2 tiles to comfortably crop a 400×250 window centered on
    # the address regardless of where in the center tile the pin sits.
    # Use 3×3 to give the crop room when the pin is near a tile edge.
    coords = [(tile_x + dx, tile_y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]

    try:
        async with httpx.AsyncClient() as client:
            results = await asyncio.gather(
                *[_fetch_tile(client, zoom, x, y) for x, y in coords],
                return_exceptions=False,
            )
    except Exception as exc:
        logger.warning(
            "Static map tile fetch failed for (%s, %s): %s: %s",
            lat, lon, type(exc).__name__, exc,
        )
        return ""

    tiles: list[tuple[int, int, bytes]] = []
    for (x, y), png in zip(coords, results):
        if png is not None:
            tiles.append((x, y, png))

    if not tiles:
        logger.warning(
            "All %d static map tiles failed for (%s, %s) — grey fallback in PDF",
            len(coords), lat, lon,
        )
        return ""

    if len(tiles) < len(coords):
        logger.info(
            "Static map: %d/%d tiles fetched for (%s, %s)",
            len(tiles), len(coords), lat, lon,
        )

    # Stitch + pin happens in a thread because Pillow ops are CPU-bound
    png = await asyncio.to_thread(
        _stitch_and_pin,
        tiles,
        cx, cy,
        tile_x - 1, tile_y - 1,
        width, height,
    )
    if png is None:
        return ""

    logger.info("Static map rendered: %d bytes for (%s, %s)", len(png), lat, lon)
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")
