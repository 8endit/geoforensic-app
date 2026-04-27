"""BfG Hochwasser-Layer (HWRM-RL nationaler Aggregat) — WMS-live query.

Source:    Bundesanstalt für Gewässerkunde (BfG) — Hochwassergefahrenkarten,
           nationaler Aggregat-Layer aus dem 2. HWRM-RL-Zyklus 2016-2021.
Endpoint:  https://geoportal.bafg.de/arcgis1/rest/services/INSPIRE/NZ/MapServer/exts/InspireView/service
License:   Datenlizenz Deutschland — Zero — Version 2.0 (DL-DE/Zero-2.0)
           — keine Attribution erforderlich, kein Copyleft, kommerziell OK
Status:    TEILWEISE VERIFIZIERT (siehe docs/DATA_SOURCES_VERIFIED.md, Layer 1)

Three flood-scenario layers per HWRM-RL:
  HQ_haeufig  — high probability, T = 5 – 20 a   ("häufiges Hochwasser")
  HQ100       — medium probability, T = 100 a    ("100-jähriges Ereignis")
  HQ_extrem   — low probability, T ≈ 1.5 × HQ100 ("extremes Ereignis")

Per address we report which (if any) of the three scenarios contains the
point. The exact INSPIRE WMS ``<Name>`` attributes for the three layers
are still pending live GetCapabilities verification (sandbox blocks the
ArcGIS endpoint with HTTP 403). Defaults below are best-guess from the
HWRM-RL convention; override via env vars if the live names differ.

Network failures, HTTP errors and parse errors all return a structured
"no-data" result with ``error`` set, so a flaky external service never
breaks PDF generation. Same defensive pattern as ``mining_nrw.py``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import xml.etree.ElementTree as ET
from typing import Any

import httpx

logger = logging.getLogger(__name__)

WMS_URL = os.getenv(
    "BFG_FLOOD_WMS_URL",
    "https://geoportal.bafg.de/arcgis1/rest/services/INSPIRE/NZ/MapServer/exts/InspireView/service",
)
LAYER_HAEUFIG = os.getenv("BFG_FLOOD_LAYER_HAEUFIG", "HQ_haeufig")
LAYER_HQ100 = os.getenv("BFG_FLOOD_LAYER_HQ100", "HQ100")
LAYER_EXTREM = os.getenv("BFG_FLOOD_LAYER_EXTREM", "HQ_extrem")
USER_AGENT = "Bodenbericht/1.0 (kontakt@geoforensic.de)"
ATTRIBUTION = (
    "Bundesanstalt für Gewässerkunde (BfG), Hochwassergefahren- und "
    "-risikokarten Deutschland, DL-DE/Zero-2.0"
)

# 0.001 deg ≈ 111 m at the equator; at NRW/middle-Germany latitudes
# this gives ~ 200 m bbox edge. WMS 1.3.0 with EPSG:4326 uses
# lat,lon axis order.
_BBOX_HALF_DEG = 0.001


def _empty_scenario(name: str) -> dict[str, Any]:
    return {"layer_name": name, "in_zone": None, "feature_count": 0, "error": None}


def _empty_result(error: str | None = None) -> dict[str, Any]:
    return {
        "any_in_zone": False,
        "scenarios": {
            "haeufig": _empty_scenario(LAYER_HAEUFIG),
            "hq100": _empty_scenario(LAYER_HQ100),
            "extrem": _empty_scenario(LAYER_EXTREM),
        },
        "attribution": ATTRIBUTION,
        "source_url": WMS_URL,
        "error": error,
    }


async def query_flood(lat: float, lon: float, timeout: float = 8.0) -> dict[str, Any]:
    """GetFeatureInfo at (lat, lon) against the BfG flood-zones WMS.

    Three independent queries in parallel — one per HQ scenario. Each
    scenario result carries::

        {
            "layer_name": str,
            "in_zone": bool | None,    # None if scenario errored
            "feature_count": int,
            "error": str | None,
        }

    Aggregate result::

        {
            "any_in_zone": bool,       # any scenario had a hit?
            "scenarios": {"haeufig": ..., "hq100": ..., "extrem": ...},
            "attribution": str,
            "source_url": str,
            "error": str | None,       # only set if ALL three failed identically
        }
    """
    bbox = (
        f"{lat - _BBOX_HALF_DEG},{lon - _BBOX_HALF_DEG},"
        f"{lat + _BBOX_HALF_DEG},{lon + _BBOX_HALF_DEG}"
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        results = await asyncio.gather(
            _query_layer(client, bbox, LAYER_HAEUFIG, lat, lon),
            _query_layer(client, bbox, LAYER_HQ100, lat, lon),
            _query_layer(client, bbox, LAYER_EXTREM, lat, lon),
            return_exceptions=False,
        )

    haeufig, hq100, extrem = results
    aggregated = {
        "any_in_zone": any(s.get("in_zone") is True for s in results),
        "scenarios": {
            "haeufig": haeufig,
            "hq100": hq100,
            "extrem": extrem,
        },
        "attribution": ATTRIBUTION,
        "source_url": WMS_URL,
        "error": None,
    }
    # If ALL three errored, expose a top-level error so the report
    # template can render "service unavailable" instead of "kein Risiko".
    errors = {s.get("error") for s in results}
    if all(s.get("in_zone") is None for s in results):
        aggregated["error"] = "all_scenarios_failed"
        if len(errors - {None}) == 1:
            aggregated["error"] = next(iter(errors - {None}))
    return aggregated


async def _query_layer(
    client: httpx.AsyncClient,
    bbox: str,
    layer: str,
    lat: float,
    lon: float,
) -> dict[str, Any]:
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetFeatureInfo",
        "LAYERS": layer,
        "QUERY_LAYERS": layer,
        "CRS": "EPSG:4326",
        "BBOX": bbox,
        "WIDTH": "101",
        "HEIGHT": "101",
        "I": "50",
        "J": "50",
        "INFO_FORMAT": "application/json",
        "FEATURE_COUNT": "5",
    }

    try:
        resp = await client.get(
            WMS_URL,
            params=params,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json,application/xml,*/*",
            },
        )
        resp.raise_for_status()
        text = resp.text
        content_type = resp.headers.get("content-type", "").lower()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "BfG flood WMS HTTP %s for layer %s at (%s, %s)",
            exc.response.status_code, layer, lat, lon,
        )
        return {**_empty_scenario(layer), "error": f"http_{exc.response.status_code}"}
    except httpx.HTTPError as exc:
        logger.warning("BfG flood WMS request failed for layer %s: %s", layer, exc)
        return {**_empty_scenario(layer), "error": "request_failed"}

    try:
        is_json = "json" in content_type or text.lstrip().startswith("{")
        if is_json:
            count = _count_json_features(text)
        else:
            count = _count_gml_features(text)
    except Exception as exc:  # noqa: BLE001 — defensive
        logger.warning("BfG flood parse failed for layer %s: %s", layer, exc)
        return {**_empty_scenario(layer), "error": "parse_failed"}

    return {
        "layer_name": layer,
        "in_zone": count > 0,
        "feature_count": count,
        "error": None,
    }


def _count_json_features(text: str) -> int:
    data = json.loads(text)
    return len(data.get("features") or [])


def _count_gml_features(text: str) -> int:
    """Crude GML feature counter — counts <member>/<featureMember> nodes."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return 0
    count = 0
    for elem in root.iter():
        local = elem.tag.split("}", 1)[-1] if "}" in elem.tag else elem.tag
        if local in ("member", "featureMember"):
            count += 1
    return count
