"""Geocode suggest endpoint — address autocomplete via Nominatim."""

import asyncio
import time

import httpx
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/geocode", tags=["geocode"])

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "GeoForensic/1.0 (kontakt@geoforensic.de)"

_lock = asyncio.Lock()
_last_call = 0.0


@router.get("/suggest")
async def geocode_suggest(
    q: str = Query(..., min_length=3),
    country: str = Query("nl,de", description="comma-sep country codes"),
) -> dict:
    """Address autocomplete via Nominatim. Rate-limited to 1 req/s."""
    global _last_call  # noqa: PLW0603

    if len(q.strip()) < 3:
        return {"suggestions": []}

    async with _lock:
        delay = 1.0 - (time.monotonic() - _last_call)
        if delay > 0:
            await asyncio.sleep(delay)

        try:
            async with httpx.AsyncClient(
                timeout=6.0,
                headers={"User-Agent": NOMINATIM_USER_AGENT},
            ) as client:
                resp = await client.get(
                    NOMINATIM_URL,
                    params={
                        "q": q,
                        "format": "json",
                        "limit": 8,
                        "addressdetails": 1,
                        "countrycodes": country,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            return {"suggestions": [], "error": str(exc)}
        finally:
            _last_call = time.monotonic()

    return {
        "suggestions": [
            {
                "label": d.get("display_name", ""),
                "lat": float(d["lat"]),
                "lon": float(d["lon"]),
                "type": d.get("type", ""),
                "class": d.get("class", ""),
            }
            for d in data
        ]
    }
