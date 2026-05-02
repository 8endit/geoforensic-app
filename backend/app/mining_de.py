"""Bundesland-Dispatcher für Bergbau-Lookups.

Routes the mining query to the right per-state WMS provider:

    - Nordrhein-Westfalen      -> mining_nrw.query_mining_nrw
    - Rheinland-Pfalz / Saarland -> mining_rlp.query_mining_rlp
                                  (LGB-RLP hostet auch SL-Daten — Oberbergamt
                                  Saarbrücken ist für beide Länder zuständig)
    - andere Bundesländer       -> kein öffentlicher WMS, returns no-data

Outputs a unified schema that section_05_bergbau.html consumes:

    {
        "available": bool,             # True wenn Provider geantwortet hat
        "in_zone": bool,               # echte Treffer im 200m-Bbox
        "provider": str,               # "NRW" | "RLP+SL" | None
        "hits": list[{                 # normalisiert für Section-Tabelle
            "name": str,
            "status": str,             # Berechtigungs-Art bzw. Risiko-Klasse
            "category": str,           # "Berechtsame" / "Altbergbau-Risiko"
            "distance_m": float | None,
        }],
        "altbergbau_risk": str | None,  # nur RLP/SL: "rot"/"gelb"/"gruen"
        "search_radius_m": int,
        "nearest_distance_m": float | None,
        "attribution": str,
        "source_urls": list[str],
        "error": str | None,
    }

Outside NRW/RLP/SL the result is the empty shell mit ``available=False`` —
das Template rendert dann den "andere Bundesländer brauchen Behörden-
Auskunft"-Placeholder.
"""

from __future__ import annotations

import logging
from typing import Any

from app.mining_nrw import query_mining_nrw
from app.mining_rlp import query_mining_rlp

logger = logging.getLogger(__name__)

# Bundesland → Provider
NRW_STATES = {"Nordrhein-Westfalen"}
RLP_SL_STATES = {"Rheinland-Pfalz", "Saarland"}

# Bbox half-width was 0.001° in both providers ≈ ~111m × ~70m near ~50°N.
# Diagonal of that bbox is the effective search radius.
_NOMINAL_SEARCH_RADIUS_M = 130


async def query_mining(
    lat: float,
    lon: float,
    state: str | None,
) -> dict[str, Any]:
    """Provider-agnostic mining query keyed by Bundesland.

    Always returns the unified schema (see module docstring) — never raises.
    Caller passes the Nominatim-derived ``state`` string (German short name).
    """
    if state in NRW_STATES:
        try:
            raw = await query_mining_nrw(lat, lon)
            return _adapt_nrw(raw)
        except Exception:
            logger.exception("NRW mining adapter failed at (%s, %s)", lat, lon)
            return _empty(provider="NRW", error="adapter_exception")

    if state in RLP_SL_STATES:
        try:
            raw = await query_mining_rlp(lat, lon)
            return _adapt_rlp(raw, state)
        except Exception:
            logger.exception("RLP mining adapter failed at (%s, %s)", lat, lon)
            return _empty(provider="RLP+SL", error="adapter_exception")

    # No public WMS for this state — Section 5 will render the placeholder.
    return _empty(provider=None)


def _empty(provider: str | None, error: str | None = None) -> dict[str, Any]:
    return {
        "available": False,
        "in_zone": False,
        "provider": provider,
        "hits": [],
        "altbergbau_risk": None,
        "search_radius_m": _NOMINAL_SEARCH_RADIUS_M,
        "nearest_distance_m": None,
        "attribution": "",
        "source_urls": [],
        "error": error,
    }


def _adapt_nrw(raw: dict[str, Any]) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    for f in raw.get("fields") or []:
        hits.append({
            "name": f.get("name") or "Bergbauberechtigung",
            "status": f.get("type") or f.get("mineral") or "—",
            "category": "Berechtsame (NRW)",
            "distance_m": None,  # WMS GetFeatureInfo gives no distance
        })
    return {
        "available": True,
        "in_zone": bool(raw.get("in_zone")),
        "provider": "NRW",
        "hits": hits,
        "altbergbau_risk": None,
        "search_radius_m": _NOMINAL_SEARCH_RADIUS_M,
        "nearest_distance_m": None,
        "attribution": raw.get("attribution") or "",
        "source_urls": [raw.get("source_url")] if raw.get("source_url") else [],
        "error": raw.get("error"),
    }


def _adapt_rlp(raw: dict[str, Any], state: str | None) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    for f in raw.get("berechtsame") or []:
        # Try to surface a meaningful "name" from typical attribute keys
        name = (
            f.get("name")
            or f.get("bezeichnung")
            or f.get("feldname")
            or f.get("category")
            or "Berechtsame"
        )
        hits.append({
            "name": str(name),
            "status": f.get("category") or "—",
            "category": "Berechtsame (LGB-RLP)",
            "distance_m": None,
        })
    if raw.get("altbergbau_risk"):
        hits.append({
            "name": "Altbergbau-Zone (Ampelkarte)",
            "status": str(raw["altbergbau_risk"]).upper(),
            "category": "Altbergbau-Risiko (LGB-RLP)",
            "distance_m": None,
        })
    provider_label = "RLP" if state == "Rheinland-Pfalz" else f"{state} via LGB-RLP"
    return {
        "available": True,
        "in_zone": bool(raw.get("in_zone")),
        "provider": provider_label,
        "hits": hits,
        "altbergbau_risk": raw.get("altbergbau_risk"),
        "search_radius_m": _NOMINAL_SEARCH_RADIUS_M,
        "nearest_distance_m": None,
        "attribution": raw.get("attribution") or "",
        "source_urls": raw.get("source_urls") or [],
        "error": raw.get("error"),
    }
