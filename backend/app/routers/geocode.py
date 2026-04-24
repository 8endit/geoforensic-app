"""Geocode suggest endpoint — address autocomplete via Nominatim."""

import httpx
from fastapi import APIRouter, Query

from app import geocode_cache

router = APIRouter(prefix="/api/geocode", tags=["geocode"])

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "GeoForensic/1.0 (kontakt@geoforensic.de)"

# Shared client — connection pooling, no per-request overhead
_client = httpx.AsyncClient(
    timeout=6.0,
    headers={"User-Agent": NOMINATIM_USER_AGENT},
    limits=httpx.Limits(max_connections=2),
)


@router.get("/suggest")
async def geocode_suggest(
    q: str = Query(..., min_length=3),
    country: str = Query("nl,de", description="comma-sep country codes"),
) -> dict:
    """Address autocomplete via Nominatim."""
    if len(q.strip()) < 3:
        return {"suggestions": []}

    cache_key = geocode_cache.key_suggest(q, country)
    cached = await geocode_cache.cache_get(cache_key)
    if isinstance(cached, list):
        return {"suggestions": cached}

    try:
        resp = await _client.get(
            NOMINATIM_URL,
            params={
                "q": q,
                "format": "json",
                "limit": 5,
                "addressdetails": 1,
                "countrycodes": country,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return {"suggestions": [], "error": str(exc)}

    suggestions = []
    seen = set()  # deduplicate by street+postal_city
    for d in data:
        addr = d.get("address", {})
        road = addr.get("road", "")
        house = addr.get("house_number", "")
        postcode = addr.get("postcode", "")
        city = (
            addr.get("city")
            or addr.get("town")
            or addr.get("village")
            or addr.get("municipality")
            or ""
        )
        country_code = addr.get("country_code", "").upper()

        street = f"{road} {house}".strip() if road else ""
        postal_city = f"{postcode} {city}".strip() if postcode or city else ""

        # Compact label for dropdown: "Strasse Nr, PLZ Stadt"
        label = street
        if postal_city:
            label = f"{label}, {postal_city}" if label else postal_city

        dedup_key = f"{street}|{postal_city}".lower()
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        suggestions.append({
            "label": label or d.get("display_name", ""),
            "street": street,
            "postal_city": postal_city,
            "country_code": country_code,
            "lat": float(d["lat"]),
            "lon": float(d["lon"]),
        })

    await geocode_cache.cache_set(cache_key, suggestions)
    return {"suggestions": suggestions}
