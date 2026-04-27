"""NRW Bergbau (mining-rights) layer — WMS-live query.

Source:    Bezirksregierung Arnsberg via wms.nrw.de
Endpoint:  https://www.wms.nrw.de/wms/wms_nw_inspire-bergbauberechtigungen
License:   Datenlizenz Deutschland — Namensnennung 2.0 (dl-de/by-2.0)
Status:    VERIFIZIERT (siehe docs/DATA_SOURCES_VERIFIED.md)

Returns mining-rights polygons that contain the query point. Used to add
a "Bergbau" section to the full report for NRW addresses. The caller
gates the section on ``region["state"] == "Nordrhein-Westfalen"`` —
non-NRW addresses should not even reach the WMS call.

Network failures, HTTP errors and parse errors all return a structured
"no-data" result with ``error`` set, so a flaky external service never
breaks PDF generation.
"""

from __future__ import annotations

import json
import logging
import os
import xml.etree.ElementTree as ET
from typing import Any

import httpx

logger = logging.getLogger(__name__)

WMS_URL = os.getenv(
    "MINING_NRW_WMS_URL",
    "https://www.wms.nrw.de/wms/wms_nw_inspire-bergbauberechtigungen",
)
# Default layer name is the German label that matches the URL slug. The
# exact INSPIRE-conformant technical name (e.g. AM.AreaManagement) needs
# to be confirmed against the live GetCapabilities — see
# docs/DATA_SOURCES_VERIFIED.md §6 for the verification command. If the
# verified name differs, override with MINING_NRW_LAYER_NAME in env.
LAYER_NAME = os.getenv("MINING_NRW_LAYER_NAME", "Bergbauberechtigungen")
USER_AGENT = "Bodenbericht/1.0 (kontakt@geoforensic.de)"
ATTRIBUTION = "Bezirksregierung Arnsberg, dl-de/by-2.0"

# Roughly 200 m bounding box around the query point. WMS 1.3.0 with
# EPSG:4326 uses lat,lon axis order. 0.001 deg latitude ~= 111 m;
# longitude shrinks with cos(lat) but at NRW latitudes (~51°) one
# arc-minute of longitude is still ~70 m — close enough for a point
# query that just needs the WMS to identify which polygon contains
# the centre pixel.
_BBOX_HALF_DEG = 0.001


def _empty_result(error: str | None = None) -> dict[str, Any]:
    return {
        "in_zone": False,
        "fields": [],
        "attribution": ATTRIBUTION,
        "source_url": WMS_URL,
        "error": error,
    }


async def query_mining_nrw(lat: float, lon: float, timeout: float = 8.0) -> dict[str, Any]:
    """GetFeatureInfo at (lat, lon) against the NRW Bergbau WMS.

    Returns a dict::

        {
            "in_zone": bool,
            "fields": [
                {
                    "name": str | None,
                    "mineral": str | None,
                    "type": str | None,
                    "valid_from": str | None,
                    "valid_to": str | None,
                    "raw": dict,
                },
                ...   # capped at 10
            ],
            "attribution": str,
            "source_url": str,
            "error": str | None,
        }

    On any failure (HTTP, parse) returns the empty shape with ``error``
    set, so the report template can render a "keine Daten" fallback.
    """
    bbox = (
        f"{lat - _BBOX_HALF_DEG},{lon - _BBOX_HALF_DEG},"
        f"{lat + _BBOX_HALF_DEG},{lon + _BBOX_HALF_DEG}"
    )
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
        "FEATURE_COUNT": "10",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(
                WMS_URL,
                params=params,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json,application/xml,*/*",
                },
            )
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "").lower()
            text = resp.text
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "NRW Bergbau WMS HTTP %s for (%s, %s)",
            exc.response.status_code, lat, lon,
        )
        return _empty_result(error=f"http_{exc.response.status_code}")
    except httpx.HTTPError as exc:
        logger.warning("NRW Bergbau WMS request failed for (%s, %s): %s", lat, lon, exc)
        return _empty_result(error="request_failed")

    fields: list[dict[str, Any]] = []
    try:
        is_json = "json" in content_type or text.lstrip().startswith("{")
        if is_json:
            fields = _parse_json_features(text)
        else:
            fields = _parse_gml_features(text)
    except Exception as exc:  # noqa: BLE001 — defensive: never crash report
        logger.warning(
            "NRW Bergbau response parse failed for (%s, %s): %s",
            lat, lon, exc,
        )
        return _empty_result(error="parse_failed")

    logger.info(
        "NRW Bergbau query (%s, %s): %d feature(s)",
        lat, lon, len(fields),
    )
    return {
        **_empty_result(),
        "in_zone": bool(fields),
        "fields": fields[:10],
    }


def _parse_json_features(text: str) -> list[dict[str, Any]]:
    data = json.loads(text)
    features = data.get("features") or []
    return [_normalize_props(feat.get("properties") or {}) for feat in features]


def _parse_gml_features(text: str) -> list[dict[str, Any]]:
    """Parse a GML FeatureCollection-style response.

    GML 3.x INSPIRE responses wrap each feature in a ``<member>`` or
    ``<gml:featureMember>`` element. We walk those, then collect the
    leaf children (text-only elements) of each feature element.
    """
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []

    out: list[dict[str, Any]] = []
    for elem in root.iter():
        local = _localname(elem)
        if local not in ("member", "featureMember"):
            continue
        # The actual feature is the single child of <member>
        for feature in elem:
            props: dict[str, Any] = {}
            for child in feature.iter():
                # Take only leaf elements with text content
                if list(child) or not (child.text and child.text.strip()):
                    continue
                props[_localname(child)] = child.text.strip()
            if props:
                out.append(_normalize_props(props))
    return out


def _localname(elem: ET.Element) -> str:
    tag = elem.tag
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _normalize_props(props: dict[str, Any]) -> dict[str, Any]:
    """Map raw attribute keys to a stable schema.

    The exact attribute names in the verified WMS schema are not yet
    locked in (see DATA_SOURCES_VERIFIED.md §6 — Capabilities-Test
    pending). We accept several plausible candidates per field. Unknown
    keys fall through into ``raw`` so nothing is silently dropped.
    """

    def pick(*candidates: str) -> str | None:
        lowered = {k.lower(): v for k, v in props.items()}
        for cand in candidates:
            val = lowered.get(cand.lower())
            if val:
                return str(val)
        return None

    return {
        "name": pick("feldname", "name", "field_name", "designation", "bezeichnung"),
        "mineral": pick("rohstoff", "mineral", "mineralResource", "bodenschatz"),
        "type": pick("art", "type", "berechtigungsart", "authorization_type"),
        "valid_from": pick("gueltig_von", "valid_from", "validFrom", "verleihung_am"),
        "valid_to": pick("gueltig_bis", "valid_to", "validTo", "befristung"),
        "raw": dict(props),
    }
