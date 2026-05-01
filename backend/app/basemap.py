"""Basemap tile fetcher for the property-context-map (visuals component #2).

Fetches CartoDB Positron tiles, composites them into a single image
centred on an address, and returns it as a base64 ``data:`` URI ready
to embed inside the SVG via ``<image href="data:image/png;base64,…">``.

Why server-side composite vs. real Slippy-Map?
----------------------------------------------
The PDF report is a static document — there is no JS runtime to drive
a Leaflet/MapLibre map. Embedding a pre-rendered tile composite gets
us a real basemap (streets, parcels, building shapes) at PDF-print
quality without a JavaScript runtime.

Source
------
CartoDB Positron, served via ``https://basemaps.cartocdn.com/`` —
CC BY 3.0, free for commercial use with attribution. Attribution
("© OpenStreetMap contributors © CARTO") is returned in the result
and must be rendered in the report footer.

Cache
-----
Tiles cached on disk under ``RASTER_DIR/tile_cache/<style>/<z>/<x>_<y>.png``
where ``RASTER_DIR`` follows the same env var convention as
``rfactor_data.py``. CartoDB ToS encourages caching.

Failure mode
------------
On any error (network, missing tiles, offline test environment) the
function returns ``available=False`` and the template falls back to a
plain grey rectangle. The visual still works, just without the basemap.
"""

from __future__ import annotations

import base64
import io
import logging
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

TILE_TEMPLATE = "https://basemaps.cartocdn.com/{style}/{z}/{x}/{y}.png"
DEFAULT_STYLE = "light_all"  # CartoDB Positron
ATTRIBUTION = "© OpenStreetMap contributors © CARTO"
TILE_PX = 256

_RASTER_DIR = os.getenv("RASTER_DIR", "/app/rasters")
_CACHE_ROOT = Path(_RASTER_DIR) / "tile_cache"

_HEADERS = {
    "User-Agent": "geoforensic-app (+https://geoforensic.de)",
}


@dataclass
class BasemapResult:
    available: bool
    image_data_uri: Optional[str] = None
    # Geographical bbox of the rendered image (lon_min, lat_min, lon_max, lat_max)
    bbox: Optional[tuple[float, float, float, float]] = None
    width_px: int = 0
    height_px: int = 0
    attribution: str = ATTRIBUTION
    style: str = DEFAULT_STYLE
    zoom: Optional[int] = None
    note: Optional[str] = None
    data_provenance: Optional[dict] = None

    def to_dict(self) -> dict:
        out = asdict(self)
        return {k: v for k, v in out.items() if v is not None}


# ---------------------------------------------------------------------------
# Web Mercator math (no GIS dep)
# ---------------------------------------------------------------------------

def lonlat_to_tile_xy(lon: float, lat: float, z: int) -> tuple[float, float]:
    """Slippy-map tile coords (continuous, not floored)."""
    n = 2.0 ** z
    x = (lon + 180.0) / 360.0 * n
    lat_rad = math.radians(lat)
    y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def tile_xy_to_lonlat(x: float, y: float, z: int) -> tuple[float, float]:
    n = 2.0 ** z
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n)))
    return lon, math.degrees(lat_rad)


def _meters_per_pixel(lat: float, z: int) -> float:
    """Web Mercator ground resolution at given lat/zoom."""
    return 156543.03392 * math.cos(math.radians(lat)) / (2.0 ** z)


def pick_zoom(radius_m: int, lat: float, target_width_px: int) -> int:
    """Pick a zoom such that the diameter (2 × radius_m) fills roughly
    ``target_width_px`` pixels. Return value is clamped to [12, 18]."""
    target_m_per_px = (2.0 * radius_m) / target_width_px
    # Find zoom where m_per_px <= target — increase zoom until it fits.
    for z in range(12, 19):
        if _meters_per_pixel(lat, z) <= target_m_per_px:
            return z
    return 18


# ---------------------------------------------------------------------------
# Tile fetching
# ---------------------------------------------------------------------------

def _cache_path(style: str, z: int, x: int, y: int) -> Path:
    return _CACHE_ROOT / style / str(z) / f"{x}_{y}.png"


def _load_or_fetch_tile(
    client: httpx.Client, style: str, z: int, x: int, y: int
) -> Optional[bytes]:
    cache_file = _cache_path(style, z, x, y)
    if cache_file.exists():
        try:
            return cache_file.read_bytes()
        except OSError:
            pass

    url = TILE_TEMPLATE.format(style=style, z=z, x=x, y=y)
    try:
        resp = client.get(url, headers=_HEADERS, timeout=10.0)
        resp.raise_for_status()
        body = resp.content
    except httpx.HTTPError as exc:
        logger.warning("tile fetch failed (%s, %d/%d/%d): %s", style, z, x, y, exc)
        return None

    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(body)
    except OSError as exc:
        logger.debug("tile cache write failed: %s", exc)
    return body


# ---------------------------------------------------------------------------
# Composite + crop
# ---------------------------------------------------------------------------

def fetch_basemap(
    lat: float,
    lon: float,
    radius_m: int = 500,
    width_px: int = 600,
    height_px: int = 320,
    style: str = DEFAULT_STYLE,
) -> dict:
    """Build a basemap-tile composite for the given centre.

    Returns a dict (see :class:`BasemapResult.to_dict`). On failure
    returns ``available=False``.
    """
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover
        return BasemapResult(
            available=False, note="Pillow nicht installiert — kein Basemap"
        ).to_dict()

    z = pick_zoom(radius_m, lat, target_width_px=width_px)
    cx, cy = lonlat_to_tile_xy(lon, lat, z)
    cx_pixel = cx * TILE_PX
    cy_pixel = cy * TILE_PX

    # The crop window in global pixel space, centred on the address.
    half_w, half_h = width_px / 2.0, height_px / 2.0
    win_left = cx_pixel - half_w
    win_top = cy_pixel - half_h

    # Tiles needed to cover the window (with one-tile padding either side).
    tile_x_min = math.floor(win_left / TILE_PX) - 1
    tile_x_max = math.ceil((win_left + width_px) / TILE_PX) + 1
    tile_y_min = math.floor(win_top / TILE_PX) - 1
    tile_y_max = math.ceil((win_top + height_px) / TILE_PX) + 1

    cols = tile_x_max - tile_x_min
    rows = tile_y_max - tile_y_min
    if cols <= 0 or rows <= 0:
        return BasemapResult(available=False, note="Ungültiges Tile-Fenster").to_dict()

    canvas = Image.new("RGB", (cols * TILE_PX, rows * TILE_PX), (240, 240, 235))
    fetched = 0
    with httpx.Client() as client:
        for ty in range(tile_y_min, tile_y_max):
            for tx in range(tile_x_min, tile_x_max):
                if ty < 0 or tx < 0 or ty >= 2 ** z or tx >= 2 ** z:
                    continue
                body = _load_or_fetch_tile(client, style, z, tx, ty)
                if body is None:
                    continue
                try:
                    tile = Image.open(io.BytesIO(body)).convert("RGB")
                    canvas.paste(
                        tile,
                        ((tx - tile_x_min) * TILE_PX, (ty - tile_y_min) * TILE_PX),
                    )
                    fetched += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning("tile decode failed (%d/%d/%d): %s", z, tx, ty, exc)

    if fetched == 0:
        return BasemapResult(
            available=False,
            note="Keine Basemap-Tiles erreichbar — Fallback auf neutralen Hintergrund.",
        ).to_dict()

    # Crop the canvas to the desired window
    crop_left = win_left - tile_x_min * TILE_PX
    crop_top = win_top - tile_y_min * TILE_PX
    crop = canvas.crop((
        int(crop_left),
        int(crop_top),
        int(crop_left + width_px),
        int(crop_top + height_px),
    ))

    # Encode as PNG with palette compression for size
    buf = io.BytesIO()
    crop.save(buf, format="PNG", optimize=True)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")

    # Bbox of the cropped window (in lon/lat)
    lon_min, lat_max = tile_xy_to_lonlat(win_left / TILE_PX, win_top / TILE_PX, z)
    lon_max, lat_min = tile_xy_to_lonlat(
        (win_left + width_px) / TILE_PX, (win_top + height_px) / TILE_PX, z
    )

    return BasemapResult(
        available=True,
        image_data_uri=f"data:image/png;base64,{encoded}",
        bbox=(lon_min, lat_min, lon_max, lat_max),
        width_px=width_px,
        height_px=height_px,
        attribution=ATTRIBUTION,
        style=style,
        zoom=z,
        data_provenance={
            "source": "CartoDB Positron (CC BY 3.0)",
            "tile_url_template": TILE_TEMPLATE.format(style=style, z="{z}", x="{x}", y="{y}"),
            "method": f"{cols}×{rows} Tile-Composit, z={z}, gecroppt auf {width_px}×{height_px} px",
            "license": "CC BY 3.0",
            "attribution": ATTRIBUTION,
        },
    ).to_dict()


def project_lonlat_to_pixel(
    lon: float,
    lat: float,
    bbox: tuple[float, float, float, float],
    width_px: int,
    height_px: int,
) -> tuple[float, float]:
    """Linear projection from a bbox to pixel coordinates inside a
    rendered basemap image. Web-Mercator is approximately linear over
    the small viewport we render (~1 km), so a linear interpolation is
    accurate to a few pixels."""
    lon_min, lat_min, lon_max, lat_max = bbox
    if lon_max == lon_min or lat_max == lat_min:
        return 0.0, 0.0
    x = (lon - lon_min) / (lon_max - lon_min) * width_px
    y = (lat_max - lat) / (lat_max - lat_min) * height_px
    return x, y


# ---------------------------------------------------------------------------
# Render context for property_context_map template
# ---------------------------------------------------------------------------

def _synthetic_bbox(lat: float, lon: float, radius_m: int) -> tuple[float, float, float, float]:
    """Build a square bbox around a point such that ``radius_m`` fits
    well inside it. Used when we don't have a real basemap (offline
    test, fallback render)."""
    # Approximate degrees per metre at this latitude (good enough at
    # property scale).
    deg_per_m_lat = 1.0 / 111_320.0
    deg_per_m_lon = 1.0 / (111_320.0 * max(0.1, math.cos(math.radians(lat))))
    half_lat = radius_m * 1.4 * deg_per_m_lat
    half_lon = radius_m * 1.4 * deg_per_m_lon
    return (lon - half_lon, lat - half_lat, lon + half_lon, lat + half_lat)


def _ampel_color_for_velocity(v: float, tokens: dict) -> str:
    bands = tokens["ampel"]
    av = abs(float(v))
    for key in ("stabil", "leicht", "moderat", "auffaellig", "erheblich", "kritisch"):
        band = bands[key]
        lo, hi = band["range_mm_per_year"]
        if lo <= av < hi:
            return band["color"]
    return bands["kritisch"]["color"]


def _separate_overlapping(
    dots: list[dict], min_dist_px: float = 8.0, max_iter: int = 6
) -> None:
    """In-place: nudge dots that are too close to each other. Simple
    O(n²) repulsion — fine for a few dozen points."""
    if len(dots) < 2:
        return
    for _ in range(max_iter):
        moved = False
        for i in range(len(dots)):
            for j in range(i + 1, len(dots)):
                dx = dots[j]["cx"] - dots[i]["cx"]
                dy = dots[j]["cy"] - dots[i]["cy"]
                dist = math.hypot(dx, dy)
                if dist >= min_dist_px:
                    continue
                # Identical-coord case: pick a deterministic offset
                # direction based on the pair index so the result is
                # stable across runs.
                if dist == 0:
                    angle = (i * 1.234 + j * 2.345) % (2 * math.pi)
                    dx = math.cos(angle)
                    dy = math.sin(angle)
                    dist = 1.0
                push = (min_dist_px - dist) / 2 + 0.5
                nx = dx / dist * push
                ny = dy / dist * push
                dots[i]["cx"] -= nx
                dots[i]["cy"] -= ny
                dots[j]["cx"] += nx
                dots[j]["cy"] += ny
                moved = True
        if not moved:
            return


def build_map_render_context(
    component: dict,
    address_lat: float,
    address_lon: float,
    basemap: Optional[dict] = None,
    tokens: Optional[dict] = None,
    map_width: int = 600,
    map_height: int = 320,
    map_x: int = 40,
    map_y: int = 80,
) -> dict:
    """Pre-compute everything the property_context_map template needs.

    The template stays declarative — all geometry (PSI projection,
    building polygon, separation jitter, ampel coloring) lives here.

    ``basemap`` is the dict returned by :func:`fetch_basemap`. Pass
    ``None`` to render without a basemap (fallback grey tile or unit
    tests).
    """
    if tokens is None:
        from app.visual_renderer import load_tokens
        tokens = load_tokens()

    radius_m = int(component.get("radius_meters") or 500)
    psi_points = component.get("psi_points") or []
    building = component.get("building_footprint")

    # Bounding box: real one from basemap, or synthetic square around address
    if basemap and basemap.get("available"):
        bbox = tuple(basemap["bbox"])  # type: ignore[assignment]
        image_data_uri = basemap.get("image_data_uri")
        attribution = basemap.get("attribution", "")
        zoom = basemap.get("zoom")
    else:
        bbox = _synthetic_bbox(address_lat, address_lon, radius_m)
        image_data_uri = None
        attribution = ""
        zoom = None

    # Project PSI points
    dots: list[dict] = []
    for p in psi_points:
        try:
            lat = float(p["lat"])
            lon = float(p["lon"])
            v = float(p["velocity"])
        except (KeyError, ValueError, TypeError):
            continue
        x, y = project_lonlat_to_pixel(lon, lat, bbox, map_width, map_height)
        # Drop points outside the visible window (with 4 px tolerance)
        if x < -4 or y < -4 or x > map_width + 4 or y > map_height + 4:
            continue
        dots.append({
            "cx": map_x + x,
            "cy": map_y + y,
            "color": _ampel_color_for_velocity(v, tokens),
            "velocity": round(v, 2),
            "coherence": float(p["coherence"]) if "coherence" in p else None,
        })
    _separate_overlapping(dots, min_dist_px=8.0)

    # Building polygon
    building_path = None
    building_centroid_xy = None
    if building and building.get("polygon"):
        coords = building["polygon"]
        pts = []
        for lon, lat in coords:
            x, y = project_lonlat_to_pixel(lon, lat, bbox, map_width, map_height)
            pts.append((map_x + x, map_y + y))
        if len(pts) >= 3:
            d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z"
            building_path = d
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            building_centroid_xy = (cx, cy)

    # Address centroid (for fallback marker if no building polygon)
    addr_x, addr_y = project_lonlat_to_pixel(
        address_lon, address_lat, bbox, map_width, map_height
    )
    address_xy = (map_x + addr_x, map_y + addr_y)

    # 500 m radius circle in pixel space
    deg_per_m_lat = 1.0 / 111_320.0
    radius_lat_deg = radius_m * deg_per_m_lat
    _, top_y = project_lonlat_to_pixel(
        address_lon, address_lat + radius_lat_deg, bbox, map_width, map_height
    )
    radius_px = abs((map_y + addr_y) - (map_y + top_y))

    return {
        "map_x": map_x,
        "map_y": map_y,
        "map_width": map_width,
        "map_height": map_height,
        "image_data_uri": image_data_uri,
        "attribution": attribution,
        "zoom": zoom,
        "psi_dots": dots,
        "building_polygon_path": building_path,
        "building_centroid_xy": building_centroid_xy,
        "address_xy": address_xy,
        "radius_px": radius_px,
        "radius_m": radius_m,
        "psi_count": len(psi_points),
    }
