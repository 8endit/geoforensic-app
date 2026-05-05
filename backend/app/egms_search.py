"""Service: EGMS Archive Search — POST gegen /insar-api/archive/query.

Findet zu einer Adresse die ueberlappenden Sentinel-1 Bursts (L2b Calibrated,
2019-2023 Release). Returns (qid, [{burst_id, filename, size, ...}, ...]).

Der qid ist ein kurzlebiges Capability-Token — er wird vom Server pro Search
ausgestellt und ist nur fuer ein paar Minuten gueltig. Heisst: Search und
Download muessen als Atomic-Pair laufen, nicht im Stundenabstand.

Auth-Modell:
- Wenn EGMS_API_TOKEN env-var gesetzt ist, schicken wir 'Authorization:
  Bearer <token>'. Das ist der saubere Pfad sobald wir einen offiziellen
  Token vom Copernicus Help-Desk haben (siehe docs/MAIL_COPERNICUS_API_TOKEN.md).
- Wenn EGMS_API_TOKEN nicht gesetzt: Service ist deaktiviert (returns
  None/empty graceful), Pipeline laeuft weiter ohne Zeitreihen-Stage.
- Cookie-basierte Auth wird BEWUSST nicht implementiert — das wuerde eine
  Browser-Session-Reuse-Architektur auf dem Server bauen, was wir nicht
  wollen (ToS + Maintenance + Sicherheit).

Code ist Auth-agnostisch: wenn der offizielle Token-Mechanismus z.B. einen
Header-Namen 'X-Api-Key' statt 'Authorization' verwendet, aendern wir nur
die `_auth_headers()`-Funktion.
"""

from __future__ import annotations

import logging
import math
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

EGMS_BASE = os.getenv("EGMS_BASE_URL", "https://egms.land.copernicus.eu")
SEARCH_PATH = "/insar-api/archive/query"
DEFAULT_TIMEOUT = 15.0

# Default-Bbox-Halbbreite um die Adresse: 2 km. Sentinel-1 Bursts sind
# ~7x20 km, ein 2 km-Polygon erwischt typischerweise 1-3 ueberlappende
# Bursts pro Bahn-Richtung. Groesser = mehr Bursts = mehr Download.
DEFAULT_BBOX_HALFSIDE_KM = 2.0


def _auth_headers() -> dict[str, str]:
    """Build auth headers from EGMS_API_TOKEN env-var.

    Returns leere dict wenn kein Token gesetzt → Caller weiss dass der
    Service de facto deaktiviert ist und kann fail-graceful.
    """
    token = os.getenv("EGMS_API_TOKEN", "").strip()
    if not token:
        return {}
    # Header-Schema kann sich aendern wenn Copernicus den finalen Mechanismus
    # spezifiziert. Aktuell vermutet (Bearer) — 1-Zeilen-Aenderung sobald
    # bestaetigt vom Help-Desk.
    return {"Authorization": f"Bearer {token}"}


def _bbox_polygon(lat: float, lon: float, halfside_km: float) -> list[list[float]]:
    """Erzeuge ein achsen-paralleles 4-Punkt-Polygon (lon/lat) um die Adresse.

    EGMS-Format ist [[lon, lat], ...] ungeschlossen. Halfside in km wird in
    Grad umgerechnet (lat ist konstant 1deg=111km, lon variiert mit cos(lat)).
    """
    deg_lat = halfside_km / 111.0
    deg_lon = halfside_km / (111.0 * max(0.1, math.cos(math.radians(lat))))
    sw = [lon - deg_lon, lat - deg_lat]
    se = [lon + deg_lon, lat - deg_lat]
    ne = [lon + deg_lon, lat + deg_lat]
    nw = [lon - deg_lon, lat + deg_lat]
    return [sw, se, ne, nw]


def is_enabled() -> bool:
    """True wenn EGMS_API_TOKEN gesetzt ist + Service einsatzbereit."""
    return bool(os.getenv("EGMS_API_TOKEN", "").strip())


async def search_bursts_for_address(
    lat: float,
    lon: float,
    halfside_km: float = DEFAULT_BBOX_HALFSIDE_KM,
    release: str = "2019-2023",
    product_levels: tuple[str, ...] = ("L2B",),
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[str | None, list[dict[str, Any]]]:
    """Suche EGMS-Bursts die das Bbox um (lat, lon) abdecken.

    Returns (qid, tiles). Bei Token fehlt: (None, []). Bei API-Fehler:
    (None, []) + log.warning. Caller behandelt leeres Ergebnis als
    "Bewegungsverlauf-Sektion bleibt 'wird nachgeliefert'".

    qid ist NUR fuer den anschliessenden Download relevant — innerhalb der
    TTL muss der Caller die Files via egms_burst_loader ziehen.
    """
    if not is_enabled():
        logger.debug("EGMS_API_TOKEN not set — egms_search disabled")
        return None, []

    poly = _bbox_polygon(lat, lon, halfside_km)
    # Query-String: timestamp als id-Param + die Produkt-Levels + Release.
    # Beobachtet aus dem reverse-engineerten execute_query() im Frontend.
    import time as _time
    qs_parts = [f"id={int(_time.time() * 1000)}"]
    for lv in product_levels:
        qs_parts.append(lv)  # z.B. "L2B"
    qs_parts.append(release)  # z.B. "2019-2023"
    url = f"{EGMS_BASE}{SEARCH_PATH}?" + "&".join(qs_parts)

    body = {"id": None, "query": poly}
    headers = {"Content-Type": "application/json", **_auth_headers()}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=body, headers=headers)
            if resp.status_code == 401:
                logger.error(
                    "EGMS search 401 — token invalid/expired. Refresh "
                    "EGMS_API_TOKEN env-var. URL hash=%s",
                    hash(url),  # log nur Hash, nicht URL (id-leak)
                )
                return None, []
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("EGMS search request failed for (%s, %s): %s", lat, lon, exc)
        return None, []

    if not data or data.get("status") != "OK":
        logger.warning(
            "EGMS search returned non-OK status for (%s, %s): %s",
            lat, lon, (data or {}).get("status"),
        )
        return None, []

    qid = data.get("id")
    # Tile-Liste-Key haengt vom Schema ab — beobachtet sind 'result_set' /
    # 'tiles' / 'hits'. Wir suchen das erste Array das Burst-Dicts enthaelt.
    tiles: list[dict] = []
    for k, v in data.items():
        if isinstance(v, list) and v and isinstance(v[0], dict) and "filename" in v[0]:
            tiles = v
            break

    logger.info(
        "egms_search took=ok qid=%s tiles=%d for (%.4f, %.4f) halfside=%.1fkm",
        qid, len(tiles), lat, lon, halfside_km,
    )
    return qid, tiles
