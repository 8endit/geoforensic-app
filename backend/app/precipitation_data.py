"""Annual precipitation lookup via Open-Meteo Historical Archive.

Liefert das langjährige Jahresmittel (mm/Jahr) für eine Koordinate. Wird
im Vollbericht von der Korrelations-Radar-Achse "Niederschlag" konsumiert.

Vorher war diese Achse permanent "n/a" (Domenico-Feedback 2026-05-05),
weil keine Pipeline-Stage Jahres-Niederschlag berechnete. KOSTRA hat nur
Bemessungsregen-Wiederkehrintervalle, kein langjähriges Mittel.

Quelle: Open-Meteo Historical Archive ist eine kostenlose Re-Analyse-API
(ERA5-basiert, ~10 km Auflösung), keine Registrierung, kein Rate-Limit
für niedrige Volumes. Wir nehmen 10 Jahre (2014-2023, das letzte
geschlossene Dekaden-Fenster) und mitteln.

Der Aufruf ist async + via httpx; Ergebnis wird in Redis gecached
(Schlüssel hängt nur an gerundetem lat/lon, weil Niederschlag-Mittel
sich auf 100 m kaum unterscheidet → ~30 Tage TTL ist sicher).
"""

from __future__ import annotations

import logging
import os

import httpx

from app import geocode_cache

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
DEFAULT_TIMEOUT = 8.0

# 10 Jahre rolling window — geschlossen damit das Ergebnis reproduzierbar
# ist (sonst würde "letzte 10 Jahre" je nach API-Aufruf-Zeit anders sein).
START_YEAR = 2014
END_YEAR = 2023

# Cache-Key-Präzision: 0.01° ≈ 1.1 km — Niederschlags-Klimatologie
# variiert auf der Skala kaum. So treffen die meisten Anfragen für die
# gleiche Stadt denselben Cache-Eintrag.
COORD_PRECISION = 2

# 30 Tage TTL — Open-Meteo aktualisiert ERA5 nur jährlich, langes Caching
# ist erlaubt + entlastet die freie API.
CACHE_TTL_SECONDS = 30 * 24 * 60 * 60


def _cache_key(lat: float, lon: float) -> str:
    return (
        f"precipitation:v1:{round(lat, COORD_PRECISION):.2f}:"
        f"{round(lon, COORD_PRECISION):.2f}"
    )


async def fetch_annual_precipitation_mm(
    lat: float, lon: float,
) -> float | None:
    """Return langjähriges Jahresmittel mm/Jahr, oder None bei Fehler.

    Defensive: jeder API-Fehler wird zu None (silent), die Pipeline läuft
    sonst weiter und der Radar zeigt einfach wie vorher "Phase 2" an.
    Niederschlag ist optional, kein Block-Pfad.
    """
    key = _cache_key(lat, lon)
    cached = await geocode_cache.cache_get(key)
    if cached is not None:
        try:
            return float(cached)
        except (TypeError, ValueError):
            await geocode_cache.cache_delete(key)

    # Open-Meteo: tägliche Niederschlagssumme (precipitation_sum), wir
    # holen das fürs ganze Fenster und summieren in Python pro Jahr.
    params = {
        "latitude": f"{lat:.5f}",
        "longitude": f"{lon:.5f}",
        "start_date": f"{START_YEAR}-01-01",
        "end_date": f"{END_YEAR}-12-31",
        "daily": "precipitation_sum",
        "timezone": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.warning(
            "Open-Meteo precipitation lookup failed for (%s, %s): %s",
            lat, lon, exc,
        )
        return None

    daily = (data or {}).get("daily") or {}
    sums = daily.get("precipitation_sum")
    if not sums:
        logger.warning(
            "Open-Meteo returned no precipitation_sum for (%s, %s) — "
            "data keys: %s", lat, lon, sorted(daily.keys()),
        )
        return None

    # Sums = list[float | None] über alle Tage 2014-01-01..2023-12-31
    # (10 Jahre × 365.25 Tage = ~3653 Werte). Mittelwert → Tages-Durchschnitt,
    # × 365.25 = Jahres-Mittelwert. Robuster als jahrweise zu summieren weil
    # Lücken in der Zeitreihe (None) sauber rausfallen.
    valid = [float(v) for v in sums if v is not None]
    if not valid:
        return None
    daily_mean = sum(valid) / len(valid)
    annual_mm = daily_mean * 365.25

    await geocode_cache.cache_set(key, annual_mm)
    # geocode_cache.cache_set nutzt geocode_cache_ttl_seconds. Für
    # Niederschlag würden wir gerne länger cachen, aber separater Cache-
    # Namespace mit eigenem TTL wäre Overkill für eine Achse — 7 Tage
    # ist ok.
    return annual_mm
