"""Building footprint lookup via OpenStreetMap Overpass API.

Used to render the buyer's actual building polygon on the property-context
map (visuals component #2). LoD2 (Level-of-Detail-2 building data) from
state surveying offices would be richer (height info, roof shape) but is
behind paywalls or per-state services in Germany — Phase C work. OSM
Overpass is the universal stand-in: a polygon outline good enough for a
schematic 500 m-radius map.

Strategy
--------
1. Query Overpass for ``way[building]`` within a radius around the
   address point (default 50 m — Nominatim geocodes typically land on
   the street centre line, offset from the actual building).
2. If the caller supplied ``housenumber`` + ``postcode``, prefer the
   building whose ``addr:housenumber`` and ``addr:postcode`` match
   exactly.
3. Otherwise pick the building whose centroid is closest to the input
   point.
4. If no buildings are found within radius → return ``available=False``
   so the map renderer falls back to a circle marker at the centroid.

The API target is the public Overpass instance. Timeout is generous
(15 s) because Overpass is rate-limited and can queue requests under
load. Failures degrade gracefully — the report still renders without
the polygon.
"""

from __future__ import annotations

import logging
import math
from dataclasses import asdict, dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Overpass enforces a User-Agent — bare httpx defaults trigger HTTP 406.
# The Accept header is set defensively for the same reason.
_HEADERS = {
    "User-Agent": "geoforensic-app (+https://geoforensic.de)",
    "Accept": "application/json",
}


@dataclass
class BuildingFootprintResult:
    available: bool
    polygon: Optional[list[list[float]]] = None  # [[lon, lat], ...]
    centroid: Optional[list[float]] = None  # [lon, lat]
    osm_way_id: Optional[int] = None
    match_basis: Optional[str] = None  # "housenumber" | "nearest" | None
    note: Optional[str] = None
    data_provenance: Optional[dict] = None

    def to_dict(self) -> dict:
        out = asdict(self)
        return {k: v for k, v in out.items() if v is not None}


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two lat/lon points."""
    R = 6_371_000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _polygon_centroid(coords: list[list[float]]) -> list[float]:
    """Average vertex (good enough for buildings — not a true centroid
    but close, and stable on tiny convex polygons)."""
    if not coords:
        return [0.0, 0.0]
    lon_sum = sum(c[0] for c in coords)
    lat_sum = sum(c[1] for c in coords)
    n = len(coords)
    return [lon_sum / n, lat_sum / n]


def _normalize_housenumber(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return str(value).strip().lower().replace(" ", "")


def _build_overpass_query(lat: float, lon: float, radius_m: int) -> str:
    return (
        f"[out:json][timeout:25];"
        f"way[building](around:{radius_m},{lat},{lon});"
        f"out geom;"
    )


def _parse_elements(
    elements: list[dict],
    lat: float,
    lon: float,
    housenumber: Optional[str],
    postcode: Optional[str],
) -> Optional[BuildingFootprintResult]:
    if not elements:
        return None

    target_hn = _normalize_housenumber(housenumber)
    target_pc = (postcode or "").strip()

    candidates: list[tuple[float, dict]] = []
    for el in elements:
        geom = el.get("geometry") or []
        if len(geom) < 3:
            continue
        coords = [[g["lon"], g["lat"]] for g in geom]
        centroid = _polygon_centroid(coords)
        dist = _haversine_m(lat, lon, centroid[1], centroid[0])
        candidates.append((dist, {
            "way_id": el.get("id"),
            "tags": el.get("tags") or {},
            "polygon": coords,
            "centroid": centroid,
            "distance_m": dist,
        }))

    if not candidates:
        return None

    # Prefer exact addr:housenumber + addr:postcode match
    if target_hn and target_pc:
        for _, c in candidates:
            tags = c["tags"]
            if (
                _normalize_housenumber(tags.get("addr:housenumber")) == target_hn
                and (tags.get("addr:postcode") or "").strip() == target_pc
            ):
                return BuildingFootprintResult(
                    available=True,
                    polygon=c["polygon"],
                    centroid=c["centroid"],
                    osm_way_id=c["way_id"],
                    match_basis="housenumber",
                    data_provenance={
                        "source": "OpenStreetMap (Overpass API)",
                        "url": OVERPASS_URL,
                        "method": "addr:housenumber + addr:postcode tag match",
                        "license": "ODbL",
                    },
                )

    # Fallback: nearest building by centroid distance
    candidates.sort(key=lambda t: t[0])
    nearest = candidates[0][1]
    return BuildingFootprintResult(
        available=True,
        polygon=nearest["polygon"],
        centroid=nearest["centroid"],
        osm_way_id=nearest["way_id"],
        match_basis="nearest",
        note=(
            f"Nächstgelegenes OSM-Gebäude im Suchradius "
            f"(~{nearest['distance_m']:.0f} m vom Adress-Punkt). "
            "Hausnummern-genaue Zuordnung in OpenStreetMap nicht verfügbar."
        ),
        data_provenance={
            "source": "OpenStreetMap (Overpass API)",
            "url": OVERPASS_URL,
            "method": "nearest-centroid in radius",
            "license": "ODbL",
        },
    )


async def query_building_footprint(
    lat: float,
    lon: float,
    housenumber: Optional[str] = None,
    postcode: Optional[str] = None,
    radius_m: int = 50,
    timeout: float = 15.0,
) -> dict:
    """Look up a building polygon for an address. Always returns a
    dict with ``available: bool`` so callers can branch without
    handling exceptions."""
    query = _build_overpass_query(lat, lon, radius_m)

    try:
        async with httpx.AsyncClient(timeout=timeout, headers=_HEADERS) as client:
            resp = await client.post(OVERPASS_URL, data=query)
            resp.raise_for_status()
            payload = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("Overpass request failed: %s", exc)
        return BuildingFootprintResult(
            available=False,
            note="OpenStreetMap Overpass derzeit nicht erreichbar.",
        ).to_dict()
    except ValueError as exc:
        logger.warning("Overpass returned non-JSON: %s", exc)
        return BuildingFootprintResult(
            available=False,
            note="OpenStreetMap Overpass lieferte ungültige Antwort.",
        ).to_dict()

    elements = payload.get("elements") or []
    result = _parse_elements(elements, lat, lon, housenumber, postcode)
    if result is None:
        return BuildingFootprintResult(
            available=False,
            note=f"Im {radius_m} m-Radius kein Gebäude in OSM kartiert.",
        ).to_dict()
    return result.to_dict()
