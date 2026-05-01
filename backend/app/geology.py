"""Geological context via BGR GÜK250 ArcGIS REST.

Migrated 2026-05-01 from ProofTrailAgents (`geoforensic/backend/reports/
geology.py`). The original used the BGR WMS GetFeatureInfo on the
GÜK200 endpoint (`services.bgr.de/wms/geologie/guek200/`). That
endpoint now rejects bare GetCapabilities/GetFeatureInfo requests with
HTTP 400 (verified 2026-05-01).

The working alternative is the BGR ArcGIS REST endpoint for GÜK250
(harmonized 1:250 000 geological overview map of Germany):

    https://services.bgr.de/arcgis/rest/services/geologie/guek250/MapServer/identify

Data difference vs. GÜK200: same source dataset, slightly coarser
generalisation (1:250 000 vs. 1:200 000). Functionally identical for our
purpose — telling a buyer what stratigraphic unit and rock type sits
under their address.

Country routing
---------------
DE only. NL/AT/CH callers receive ``available=False`` with a note. The
LGRB BW Hydrogeologie endpoint (also DE-only, BW only) is a separate
module — V.0.x — not part of this geology stub.

Provenance (V.0.6 additive)
---------------------------
The result dict includes a ``data_provenance`` block on every
``available=True`` response so the visuals can render exact source
attribution.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

BGR_GUEK250_IDENTIFY_URL = (
    "https://services.bgr.de/arcgis/rest/services/"
    "geologie/guek250/MapServer/identify"
)

# Layer IDs in the GUEK250 MapServer (verified 2026-05-01):
#   5 = guek250_Basislayer_Stratigraphie  → age (Holozän, Pleistozän, …)
#   8 = guek250_Basislayer_Petrographie   → rock type (Lockergestein, …)
LAYER_STRATIGRAPHIE = 5
LAYER_PETROGRAPHIE = 8

# Coarse Germany-bounds gate. Outside this box we don't even hit the
# service; we return unavailable directly. Values are Germany's actual
# bounding envelope (lon_min, lat_min, lon_max, lat_max) — tighter than
# the BGR coverage which extends a few km into NL/PL/CH for border
# clarity, but those border cases are filtered by country_code anyway.
DE_BBOX = (5.87, 47.27, 15.04, 55.06)


@dataclass
class GeologyResult:
    available: bool
    source: str
    rock_type: Optional[str] = None
    rock_type_short: Optional[str] = None
    stratigraphy: Optional[str] = None
    stratigraphy_age: Optional[str] = None
    legend_text: Optional[str] = None
    risks: Optional[list[str]] = None
    note: Optional[str] = None
    data_provenance: Optional[dict] = None

    def to_dict(self) -> dict:
        out = asdict(self)
        return {k: v for k, v in out.items() if v is not None}


def _unavailable(reason: str) -> GeologyResult:
    return GeologyResult(
        available=False,
        source="BGR GÜK250",
        note=reason,
    )


def _in_germany(lat: float, lon: float) -> bool:
    lon_min, lat_min, lon_max, lat_max = DE_BBOX
    return lon_min <= lon <= lon_max and lat_min <= lat <= lat_max


def _derive_risks(text: str) -> list[str]:
    risks: list[str] = []
    text_low = text.lower()
    if any(k in text_low for k in ("ton", "tonstein", "mergel", "pelit")):
        risks.append("Quell- und Schrumpfböden möglich (Tonmineralien)")
    if "karst" in text_low or "kalkstein" in text_low:
        risks.append("Karstverkarstungsrisiko — Hohlräume im Untergrund möglich")
    if "torf" in text_low or "moor" in text_low or "humos" in text_low:
        risks.append("Organische Böden — erhöhtes Setzungspotenzial")
    if any(k in text_low for k in ("bergbau", "stollen", "abbau")):
        risks.append("Historischer Bergbau — Senkungsrisiko")
    if "lockergestein" in text_low and "psephit" in text_low:
        risks.append("Wechselnde Korngrößen (Kies/Sand/Schluff) — heterogene Tragfähigkeit")
    return risks


def _parse_identify_response(payload: dict) -> Optional[GeologyResult]:
    results = payload.get("results") or []
    if not results:
        return None

    strat: dict[str, Any] = {}
    petro: dict[str, Any] = {}
    for r in results:
        layer_id = r.get("layerId")
        attrs = r.get("attributes") or {}
        if layer_id == LAYER_STRATIGRAPHIE and not strat:
            strat = attrs
        elif layer_id == LAYER_PETROGRAPHIE and not petro:
            petro = attrs

    if not strat and not petro:
        return None

    stratigraphy = strat.get("Stratigraphie - gesamt") or strat.get("Legendentext")
    age = strat.get("Stratigraphie - Anfang")
    rock_short = petro.get("Petrographie - kurz")
    rock_full = petro.get("Petrographie - komplett")
    legend = petro.get("Legendentext")

    descriptive = " ".join(
        v for v in (stratigraphy, rock_full, rock_short, legend) if v and v != "Null"
    )
    risks = _derive_risks(descriptive)

    return GeologyResult(
        available=True,
        source="BGR GÜK250 (1:250 000)",
        rock_type=rock_full,
        rock_type_short=rock_short,
        stratigraphy=stratigraphy,
        stratigraphy_age=age,
        legend_text=legend,
        risks=risks or None,
        data_provenance={
            "source": "BGR GÜK250",
            "url": BGR_GUEK250_IDENTIFY_URL,
            "resolution_m": 250,  # 1:250 000 ≈ ~250 m representational accuracy
            "method": "ArcGIS REST identify, point-in-polygon",
            "sample_count": 1,
        },
    )


async def query_geology(
    lat: float,
    lon: float,
    country_code: str = "de",
    timeout: float = 15.0,
) -> dict:
    """Look up geological context for a point. DE only.

    Returns a dict (see ``GeologyResult.to_dict``). Always returns a
    dict, never raises — failures fall back to ``available=False`` so
    the report can render a "nicht verfügbar" section.
    """
    if (country_code or "").lower() != "de":
        return _unavailable(
            "Geologische Übersichtskarte BGR GÜK250 deckt nur Deutschland ab."
        ).to_dict()

    if not _in_germany(lat, lon):
        return _unavailable(
            "Koordinate liegt außerhalb der GÜK250-Abdeckung."
        ).to_dict()

    # ArcGIS identify needs a mapExtent + imageDisplay. We use a tiny
    # window centred on the point — this is enough for point-in-polygon
    # identify, the actual pixel display size is irrelevant.
    d = 0.005
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "sr": 4326,
        "layers": f"all:{LAYER_STRATIGRAPHIE},{LAYER_PETROGRAPHIE}",
        "tolerance": 2,
        "mapExtent": f"{lon - d},{lat - d},{lon + d},{lat + d}",
        "imageDisplay": "400,400,96",
        "returnGeometry": "false",
        "f": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(BGR_GUEK250_IDENTIFY_URL, params=params)
            resp.raise_for_status()
            try:
                payload = resp.json()
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                logger.warning("BGR GÜK250 returned undecodable payload: %s", exc)
                return _unavailable(
                    "BGR GÜK250 lieferte keine auswertbare Antwort."
                ).to_dict()

            result = _parse_identify_response(payload)
            if result is None:
                return _unavailable(
                    "Keine geologischen Einheiten am Standort kartiert."
                ).to_dict()
            return result.to_dict()
    except httpx.HTTPError as exc:
        logger.warning("BGR GÜK250 request failed: %s", exc)
        return _unavailable(
            "BGR GÜK250 derzeit nicht erreichbar."
        ).to_dict()
