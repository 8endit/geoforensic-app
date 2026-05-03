"""Rheinland-Pfalz + Saarland Bergbau-Layer — WMS-live query.

Source:    LGB-RLP (Landesamt für Geologie und Bergbau Rheinland-Pfalz)
Endpoints:
  - Berechtsamskarte: https://mapserver.lgb-rlp.de/cgi-bin/mc_berechtsamskarte
    (3 Layer: brs_erdwaerme, brs_kohlenwasserstoffe, brs_lithium)
  - Altbergbau Ampelkarte: https://mapserver.lgb-rlp.de/cgi-bin/mc_aak
    (Layer: AltbergbauAmpel — Risiko-Klassifikation historischer Bergbau-Zonen)
License:   Datenlizenz Deutschland — Namensnennung 2.0 (dl-de/by-2.0)
Status:    VERIFIZIERT 2026-05-02 (GetCapabilities beider Endpoints geliefert)

Coverage: das Oberbergamt Saarbrücken ist für RLP UND Saarland zuständig,
die LGB-RLP-Daten decken vermutlich auch Saarland mit ab. Der Aufrufer
sollte diese Funktion für `state in {"Rheinland-Pfalz", "Saarland"}` nutzen.

Returns mining-rights polygons (Berechtsame) plus historical-mining
risk traffic-light classification (Altbergbau-Ampel) at the query point.
"""

from __future__ import annotations

import json
import logging
import os
import xml.etree.ElementTree as ET
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BERECHTSAME_URL = os.getenv(
    "MINING_RLP_BERECHTSAME_URL",
    "https://mapserver.lgb-rlp.de/cgi-bin/mc_berechtsamskarte",
)
ALTBERGBAU_URL = os.getenv(
    "MINING_RLP_ALTBERGBAU_URL",
    "https://mapserver.lgb-rlp.de/cgi-bin/mc_aak",
)
BERECHTSAME_LAYERS = ["brs_erdwaerme", "brs_kohlenwasserstoffe", "brs_lithium"]
ALTBERGBAU_LAYER = "AltbergbauAmpel"
USER_AGENT = "Bodenbericht/1.0 (kontakt@geoforensic.de)"
ATTRIBUTION = "LGB Rheinland-Pfalz, dl-de/by-2.0"

_BBOX_HALF_DEG = 0.001


async def query_mining_rlp(lat: float, lon: float, timeout: float = 8.0) -> dict[str, Any]:
    """Query both LGB-RLP WMS for Berechtsame and Altbergbau-Ampel.

    Returns aggregated dict::

        {
            "in_zone": bool,                 # any berechtsame OR altbergbau hit
            "berechtsame": list[dict],       # Erdwaerme + Kohlenwasserstoffe + Lithium
            "altbergbau_risk": str | None,   # "rot"/"gelb"/"gruen" if AAK responded
            "altbergbau_raw": list[dict],
            "attribution": str,
            "source_urls": [str, str],
            "error": str | None,
        }

    Failure-tolerant: if one of the two WMS errors, the other still runs
    and returns its data.
    """
    out: dict[str, Any] = {
        "in_zone": False,
        "berechtsame": [],
        "altbergbau_risk": None,
        "altbergbau_raw": [],
        "attribution": ATTRIBUTION,
        "source_urls": [BERECHTSAME_URL, ALTBERGBAU_URL],
        "error": None,
    }

    bbox = (
        f"{lat - _BBOX_HALF_DEG},{lon - _BBOX_HALF_DEG},"
        f"{lat + _BBOX_HALF_DEG},{lon + _BBOX_HALF_DEG}"
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Berechtsame: query each layer separately so a single layer error
        # doesn't poison the others.
        for layer in BERECHTSAME_LAYERS:
            features = await _wms_get_feature_info(
                client, BERECHTSAME_URL, layer, bbox,
            )
            for feat in features:
                feat["layer"] = layer
                feat["category"] = _label_for_layer(layer)
            out["berechtsame"].extend(features)

        # Altbergbau-Ampel: single layer, gibt Risiko-Klassifikation
        aak_features = await _wms_get_feature_info(
            client, ALTBERGBAU_URL, ALTBERGBAU_LAYER, bbox,
        )
        out["altbergbau_raw"] = aak_features
        out["altbergbau_risk"] = _extract_ampel_risk(aak_features)

    out["in_zone"] = bool(out["berechtsame"]) or out["altbergbau_risk"] is not None
    return out


def _label_for_layer(layer: str) -> str:
    return {
        "brs_erdwaerme": "Erdwärme-Berechtsame",
        "brs_kohlenwasserstoffe": "Kohlenwasserstoff-Berechtsame",
        "brs_lithium": "Lithium-Berechtsame",
    }.get(layer, layer)


async def _wms_get_feature_info(
    client: httpx.AsyncClient,
    url: str,
    layer: str,
    bbox: str,
) -> list[dict[str, Any]]:
    """GetFeatureInfo for one WMS layer at the given bbox center."""
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
        "FEATURE_COUNT": "10",
    }
    try:
        resp = await client.get(
            url, params=params,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json,*/*"},
        )
        resp.raise_for_status()
        text = resp.text
        ct = resp.headers.get("content-type", "").lower()
    except httpx.HTTPError as exc:
        logger.warning("LGB-RLP %s/%s lookup failed: %s", url, layer, exc)
        return []

    try:
        if "json" in ct or text.lstrip().startswith("{"):
            data = json.loads(text)
            return [feat.get("properties") or {} for feat in (data.get("features") or [])]
        # GML fallback
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            return []
        out: list[dict[str, Any]] = []
        for elem in root.iter():
            local = elem.tag.split("}", 1)[-1]
            if local not in ("member", "featureMember"):
                continue
            for feature in elem:
                props: dict[str, Any] = {}
                for child in feature.iter():
                    if list(child) or not (child.text and child.text.strip()):
                        continue
                    key = child.tag.split("}", 1)[-1]
                    props[key] = child.text.strip()
                if props:
                    out.append(props)
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("LGB-RLP %s/%s parse failed: %s", url, layer, exc)
        return []


_RISK_RANK = {"rot": 3, "gelb": 2, "gruen": 1}


def _classify_one(feat: dict[str, Any]) -> str | None:
    """Classify a single AAK feature into 'rot' / 'gelb' / 'gruen' / raw / None."""
    lowered = {k.lower(): v for k, v in feat.items()}
    for key in ("ampel", "risiko", "kategorie", "klasse", "color", "farbe"):
        val = lowered.get(key)
        if val:
            v = str(val).lower()
            if "rot" in v or "hoch" in v or "high" in v:
                return "rot"
            if "gelb" in v or "mittel" in v or "yellow" in v:
                return "gelb"
            if "gruen" in v or "grün" in v or "niedrig" in v or "green" in v:
                return "gruen"
            return str(val)
    return None


def _extract_ampel_risk(features: list[dict[str, Any]]) -> str | None:
    """Map AAK feature properties to a Ampel-Klasse string.

    The AAK ("Altbergbau Ampelkarte") encodes risk via a category attribute.
    Without a verified attribute name we look at common candidates and
    fall back to "vorhanden" if any feature was returned but none classified.

    When multiple polygons overlap at the queried point (e.g. a Berechtsame
    plus an old-mining hot-spot), we return the *worst* classification so
    we never silently downgrade a red zone because a green polygon was
    listed first in the WMS response.
    """
    if not features:
        return None
    classified: list[str] = [c for c in (_classify_one(f) for f in features) if c]
    if not classified:
        # WMS returned features but none matched our heuristic — flag presence.
        return "vorhanden"
    # Pick the worst by ordered ranking; unknown raw values rank below rot/gelb/gruen.
    return max(classified, key=lambda c: _RISK_RANK.get(c, 0))
