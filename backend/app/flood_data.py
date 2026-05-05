"""BfG Hochwasser-Layer (HWRM-RL nationaler Aggregat) — WMS-live query.

Source:    Bundesanstalt für Gewässerkunde (BfG) — Hochwassergefahrenkarten,
           nationaler Aggregat aus dem 2. HWRM-RL-Zyklus 2016-2021.
License:   Datenlizenz Deutschland — Zero — Version 2.0 (DL-DE/Zero-2.0)
           — keine Attribution erforderlich, kein Copyleft, kommerziell OK
Status:    VERIFIZIERT vom VPS (2026-04-29) — siehe Service-Discovery
           in scripts/check-bfg-layers.sh, Output dort

The BfG geoportal exposes the three HWRM scenarios as **separate WMS
services**, not as three layers within one service. Each service has a
single layer at the generic ArcGIS index name "0":

    HWRMRL_DE_SL  — Low probability  → HQ haeufig (T = 5–20 a)
    HWRMRL_DE_SM  — Medium probability → HQ100   (T = 100 a)
    HWRMRL_DE_SH  — High probability  → HQ extrem (T ≈ 1.5 × HQ100)

Per address we report which (if any) of the three scenarios contains the
point. Each query runs against its own URL in parallel.

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

# Each scenario is a separate ArcGIS MapServer service. The WMS layer
# inside each service is always called "0" (ArcGIS default for a single-
# layer MapServer). Override service URLs via env vars if the BfG renames
# them; the layer name itself is unlikely to change.
_BASE = "https://geoportal.bafg.de/arcgis1/services/HWRMRL"

WMS_URL_HAEUFIG = os.getenv(
    "BFG_FLOOD_URL_HAEUFIG",
    f"{_BASE}/HWRMRL_DE_SL/MapServer/WMSServer",
)
WMS_URL_HQ100 = os.getenv(
    "BFG_FLOOD_URL_HQ100",
    f"{_BASE}/HWRMRL_DE_SM/MapServer/WMSServer",
)
WMS_URL_EXTREM = os.getenv(
    "BFG_FLOOD_URL_EXTREM",
    f"{_BASE}/HWRMRL_DE_SH/MapServer/WMSServer",
)
LAYER_NAME = os.getenv("BFG_FLOOD_LAYER_NAME", "0")

USER_AGENT = "Bodenbericht/1.0 (kontakt@geoforensic.de)"
ATTRIBUTION = (
    "Bundesanstalt für Gewässerkunde (BfG), Hochwassergefahren- und "
    "-risikokarten Deutschland, DL-DE/Zero-2.0"
)

# 0.001 deg ≈ 111 m at the equator; at NRW/middle-Germany latitudes
# this gives ~ 200 m bbox edge. WMS 1.3.0 with EPSG:4326 uses
# lat,lon axis order.
_BBOX_HALF_DEG = 0.001


def _empty_scenario(scenario: str, url: str) -> dict[str, Any]:
    return {
        "scenario": scenario,
        "service_url": url,
        "in_zone": None,
        "feature_count": 0,
        "error": None,
    }


def _empty_result(error: str | None = None) -> dict[str, Any]:
    return {
        "any_in_zone": False,
        "scenarios": {
            "haeufig": _empty_scenario("haeufig", WMS_URL_HAEUFIG),
            "hq100": _empty_scenario("hq100", WMS_URL_HQ100),
            "extrem": _empty_scenario("extrem", WMS_URL_EXTREM),
        },
        "attribution": ATTRIBUTION,
        "error": error,
    }


async def query_flood(lat: float, lon: float, timeout: float = 8.0) -> dict[str, Any]:
    """GetFeatureInfo at (lat, lon) against the three BfG HWRM services.

    Three independent queries in parallel — one per HQ scenario, each
    against its own service URL. Each scenario result carries::

        {
            "scenario": "haeufig" | "hq100" | "extrem",
            "service_url": str,
            "in_zone": bool | None,    # None if scenario errored
            "feature_count": int,
            "error": str | None,
        }

    Aggregate result::

        {
            "any_in_zone": bool,
            "scenarios": {"haeufig": ..., "hq100": ..., "extrem": ...},
            "attribution": str,
            "error": str | None,        # only set if all three failed
        }
    """
    bbox = (
        f"{lat - _BBOX_HALF_DEG},{lon - _BBOX_HALF_DEG},"
        f"{lat + _BBOX_HALF_DEG},{lon + _BBOX_HALF_DEG}"
    )

    targets = [
        ("haeufig", WMS_URL_HAEUFIG),
        ("hq100", WMS_URL_HQ100),
        ("extrem", WMS_URL_EXTREM),
    ]

    async with httpx.AsyncClient(timeout=timeout) as client:
        results = await asyncio.gather(
            *[_query_service(client, bbox, scenario, url, lat, lon) for scenario, url in targets],
            return_exceptions=False,
        )

    by_scenario = {r["scenario"]: r for r in results}
    aggregated = {
        "any_in_zone": any(r.get("in_zone") is True for r in results),
        "scenarios": by_scenario,
        "attribution": ATTRIBUTION,
        "error": None,
    }

    # If ALL three errored, expose a top-level error so the report
    # template can render "service unavailable" instead of "kein Risiko".
    if all(r.get("in_zone") is None for r in results):
        aggregated["error"] = "all_scenarios_failed"
        errors = {r.get("error") for r in results} - {None}
        if len(errors) == 1:
            aggregated["error"] = next(iter(errors))
    return aggregated


async def _query_service(
    client: httpx.AsyncClient,
    bbox: str,
    scenario: str,
    url: str,
    lat: float,
    lon: float,
) -> dict[str, Any]:
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetFeatureInfo",
        "LAYERS": LAYER_NAME,
        "QUERY_LAYERS": LAYER_NAME,
        "CRS": "EPSG:4326",
        "BBOX": bbox,
        "WIDTH": "101",
        "HEIGHT": "101",
        "I": "50",
        "J": "50",
        "INFO_FORMAT": "application/json",
        "FEATURE_COUNT": "5",
    }

    # BfG-WMS ist transient flaky (504 / connection-reset waehrend
    # Maintenance-Fenstern). Drei Versuche mit exponential backoff
    # 0 / 0.5 / 1.5s — reicht fuer typische 1-2s Glitches und kostet
    # bei normalem Erfolg null Zeit (erster try succeeded sofort).
    last_exc: Exception | None = None
    text = ""
    content_type = ""
    for attempt in range(3):
        try:
            resp = await client.get(
                url,
                params=params,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json,application/xml,*/*",
                },
            )
            resp.raise_for_status()
            text = resp.text
            content_type = resp.headers.get("content-type", "").lower()
            last_exc = None
            break
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            # 5xx → retry; 4xx → sofort aufgeben (kein Server-Glitch).
            if 500 <= exc.response.status_code < 600 and attempt < 2:
                await asyncio.sleep(0.5 * (1 + attempt))
                continue
            logger.warning(
                "BfG flood WMS HTTP %s for scenario %s at (%s, %s) "
                "after %d attempt(s)",
                exc.response.status_code, scenario, lat, lon, attempt + 1,
            )
            return {
                **_empty_scenario(scenario, url),
                "error": f"http_{exc.response.status_code}",
            }
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt < 2:
                await asyncio.sleep(0.5 * (1 + attempt))
                continue
            logger.warning(
                "BfG flood WMS request failed for scenario %s after %d attempt(s): %s",
                scenario, attempt + 1, exc,
            )
            return {**_empty_scenario(scenario, url), "error": "request_failed"}
    if last_exc is not None:  # safety: alle 3 retries fehlgeschlagen
        return {**_empty_scenario(scenario, url), "error": "request_failed"}

    try:
        is_json = "json" in content_type or text.lstrip().startswith("{")
        if is_json:
            count = _count_json_features(text)
        else:
            count = _count_gml_features(text)
    except Exception as exc:  # noqa: BLE001 — defensive
        logger.warning(
            "BfG flood parse failed for scenario %s: %s",
            scenario, exc,
        )
        return {**_empty_scenario(scenario, url), "error": "parse_failed"}

    return {
        "scenario": scenario,
        "service_url": url,
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
