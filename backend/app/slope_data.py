"""Slope / elevation analysis via Open-Elevation API (multi-scale probing).

Queries elevation at 13 points around each address (centre + 4 cardinal probes
at 50 m / 150 m / 500 m offsets) and reports the steepest detected slope —
catches both local terrain (Hanglage 50 m) and broader valley/ridge
transitions (500 m). Returns slope angle in degrees, aspect in 0-360°, and
a German classification.

Why this matters for the report:
    soil_directive.py runs RUSLE A = R × K × LS × C × P; the LS factor
    depends on slope. Without a real slope value the default 2° understates
    erosion for hillside addresses. With slope from this module the RUSLE
    output for hillside parcels (Stuttgart, Heidelberg, Vogesen, Rhine
    valley sides) becomes meaningful.

Sources, in order of preference:
    1. OpenTopoData (https://api.opentopodata.org/v1/srtm30m) — free public,
       SRTM 1-arcsec, 1 000 req/day, max 100 locations per request.
    2. Open-Elevation (https://api.open-elevation.com/api/v1/lookup) — same
       SRTM data, MIT licence, self-hostable. Currently flaky (504 timeouts
       observed 2026-04-30) so kept only as fallback.

Phase C will add:
    - AHN WCS for NL (0.5 m LiDAR precision, replaces SRTM for NL)
    - local SRTM-tile cache for DE so we don't depend on public APIs

Ported from ProofTrailAgents/geoforensic/backend/reports/slope_analysis.py.
"""

from __future__ import annotations

import asyncio
import logging
import math

import httpx

logger = logging.getLogger(__name__)

_OPENTOPO_URL = "https://api.opentopodata.org/v1/srtm30m"
_OPENELEV_URL = "https://api.open-elevation.com/api/v1/lookup"
_PROBE_OFFSETS_M = (50.0, 150.0, 500.0)


def _offset_point(lat: float, lon: float, dx_m: float, dy_m: float) -> tuple[float, float]:
    """Return (lat, lon) offset by dx_m east and dy_m north."""
    dlat = dy_m / 111_320.0
    dlon = dx_m / (111_320.0 * max(math.cos(math.radians(lat)), 0.01))
    return lat + dlat, lon + dlon


def _classify(slope_deg: float) -> str:
    if slope_deg < 5:
        return "flach"
    if slope_deg < 15:
        return "leicht geneigt"
    if slope_deg < 30:
        return "Hanglage"
    return "Steilhang"


def _aspect_label(deg: float) -> str:
    """Convert 0-360 bearing to N/NE/E/SE/S/SW/W/NW."""
    labels = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((deg + 22.5) / 45.0) % 8
    return labels[idx]


async def _query_elevation(
    points: list[tuple[float, float]],
) -> tuple[list[float], str] | tuple[None, str]:
    """Try OpenTopoData first, fall back to Open-Elevation.
    Returns ``(elevations, source_label)`` or ``(None, reason)``.
    """
    try:
        loc_str = "|".join(f"{lat},{lon}" for lat, lon in points)
        async with httpx.AsyncClient(timeout=20.0) as client:
            for attempt in range(3):
                resp = await client.get(_OPENTOPO_URL, params={"locations": loc_str})
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    if len(results) >= len(points):
                        return ([r.get("elevation", 0.0) or 0.0 for r in results],
                                "OpenTopoData (SRTM 1-arcsec)")
                    break
                if resp.status_code == 429:
                    await asyncio.sleep(2 * (attempt + 1))
                else:
                    logger.debug("opentopodata HTTP %s, falling back", resp.status_code)
                    break
    except Exception as exc:  # noqa: BLE001
        logger.debug("opentopodata error: %s — falling back", exc)

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            payload = {"locations": [{"latitude": lat, "longitude": lon} for lat, lon in points]}
            resp = await client.post(_OPENELEV_URL, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if len(results) >= len(points):
                    return ([float(r.get("elevation", 0.0) or 0.0) for r in results],
                            "Open-Elevation API (SRTM 1-arcsec)")
            else:
                logger.warning("open-elevation HTTP %s", resp.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("open-elevation error: %s", exc)

    return (None, "kein Elevation-Service erreichbar")


async def fetch_slope(lat: float, lon: float, country_code: str = "de") -> dict:
    """Multi-scale slope analysis via OpenTopoData / Open-Elevation.

    Returns ``{"available": True, "elevation_m", "slope_deg", "aspect_deg",
    "aspect_label", "classification", "source", "scale_m"}``  on success.
    On any upstream failure: ``{"available": False, "note": <reason>}``.

    Result wird in Redis gecached (30 Tage TTL — Hangneigung aendert
    sich praktisch nie). Damit:
    - typische Stadt-Adressen treffen ab dem 2. Lookup den Cache
    - OpenTopoData 1000 req/day-Cap wird geschont
    - Pipeline-Latenz sinkt von ~1.5s auf ~5ms wenn cached
    """
    _ = country_code  # reserved for AHN fallback in Phase C

    # Cache-Key: gerundetes lat/lon. 0.0001° ≈ 11m → praktisch adress-genau.
    from app import geocode_cache
    cache_key = (
        f"slope:v1:{round(lat, 4):.4f}:{round(lon, 4):.4f}"
    )
    cached = await geocode_cache.cache_get(cache_key)
    if cached is not None and isinstance(cached, dict):
        return cached

    all_probes: list[tuple[str, float, float]] = [("center", lat, lon)]
    for d in _PROBE_OFFSETS_M:
        all_probes.extend([
            (f"N_{int(d)}", *_offset_point(lat, lon, 0, d)),
            (f"S_{int(d)}", *_offset_point(lat, lon, 0, -d)),
            (f"E_{int(d)}", *_offset_point(lat, lon, d, 0)),
            (f"W_{int(d)}", *_offset_point(lat, lon, -d, 0)),
        ])

    results, source_label = await _query_elevation([(p[1], p[2]) for p in all_probes])
    if results is None or len(results) < len(all_probes):
        # Failed lookups NICHT cachen — naechster Aufruf soll erneut
        # versuchen (OpenTopoData ist tagsueber meist verfuegbar, geht
        # nur bei Cap-Erschoepfung 504).
        return {"available": False, "note": f"Elevation service: {source_label}"}

    elevations = {all_probes[i][0]: results[i] for i in range(len(all_probes))}
    center_elev = elevations["center"]

    best_slope = 0.0
    best_aspect = 0.0
    best_scale = 0.0
    for d in _PROBE_OFFSETS_M:
        n_key, s_key = f"N_{int(d)}", f"S_{int(d)}"
        e_key, w_key = f"E_{int(d)}", f"W_{int(d)}"
        dz_ew = (elevations[e_key] - elevations[w_key]) / (2 * d)
        dz_ns = (elevations[n_key] - elevations[s_key]) / (2 * d)
        slope_rad = math.atan(math.sqrt(dz_ew ** 2 + dz_ns ** 2))
        slope_deg = math.degrees(slope_rad)
        if slope_deg > best_slope:
            best_slope = slope_deg
            best_scale = d
            if dz_ew == 0 and dz_ns == 0:
                best_aspect = 0.0
            else:
                best_aspect = (math.degrees(math.atan2(-dz_ew, -dz_ns)) + 360) % 360

    out = {
        "available": True,
        "elevation_m": round(center_elev, 1),
        "slope_deg": round(best_slope, 2),
        "aspect_deg": round(best_aspect, 1),
        "aspect_label": _aspect_label(best_aspect),
        "classification": _classify(best_slope),
        "scale_m": int(best_scale),
        "source": source_label,
        # V.0.6 honesty-layer (additive). Documents the multi-scale
        # neighbour-probe method so the visuals can show "30 m, 90 m,
        # 300 m steepest" instead of just a slope number.
        "data_provenance": {
            "source": source_label,
            "resolution_m": int(best_scale),
            "sample_count": 1 + 4 * len(_PROBE_OFFSETS_M),
            "method": (
                f"Multi-Scale-Steepest aus 4-Punkt-Probes "
                f"(Skalen {sorted(int(d) for d in _PROBE_OFFSETS_M)} m)"
            ),
        },
    }
    # Erfolgreiche Lookups cachen — Hangneigung aendert sich nie.
    await geocode_cache.cache_set(cache_key, out)
    return out
