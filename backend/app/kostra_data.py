"""DWD KOSTRA-DWD-2020 starkregen lookups.

Source:    DWD CDC OpenData — KOSTRA-DWD-2020
License:   GeoNutzV (commercial use OK with source attribution)
DOI:       10.5676/DWD/KOSTRA-DWD-2020
Status:    TEILWEISE VERIFIZIERT (license green, no WMS, raster download)
           Siehe docs/DATA_SOURCES_VERIFIED.md (Layer 4)

Loads the GeoTIFFs produced by ``scripts/download_kostra.py`` from
``RASTER_DIR/kostra_dwd_2020/`` and exposes a per-address lookup. Each
slot represents one (Dauerstufe, Wiederkehrintervall) combination; we
ship a small fixed set that covers the buyer-relevant cases:

- 60 min / T=100 a — short-duration heavy rain (Keller, Hänge)
- 24 h  / T=100 a — Jahrhundert-Tageshochwasser-Niederschlag
- 24 h  / T=10  a — relativ häufiges Tageshochwasser

If the rasters are not (yet) on disk, the loader degrades gracefully:
``query()`` returns the slot list with ``value=None``, and the report
template renders a "Daten in Vorbereitung"-Zustand. So this module is
safe to deploy before the operator has run the download script.

Filename-Schema:
    KOSTRA filenames follow a tag pattern that includes Dauerstufe (Dxx)
    and Wiederkehr (Tyy). The exact technical filenames as produced by
    DWD are not yet locked in (see DATA_SOURCES_VERIFIED.md §6 — first
    download from VPS pending). The glob patterns below are best-guess
    and tolerant of minor naming variations; the operator can override
    via the KOSTRA_<slot>_GLOB env vars if the actual filenames differ.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from app.soil_data import RasterLookup, _NODATA

logger = logging.getLogger(__name__)

RASTER_DIR = os.getenv("RASTER_DIR", "/app/rasters")
KOSTRA_SUBDIR = "kostra_dwd_2020"
ATTRIBUTION = "Deutscher Wetterdienst, KOSTRA-DWD-2020 (DOI 10.5676/DWD/KOSTRA-DWD-2020)"

KOSTRA_SLOTS: dict[str, dict[str, str]] = {
    # 60min Starkregen (Sommergewitter-Spektrum)
    "d60min_t1a": {
        "glob_default": "*D60*T1a*.tif",
        "label": "60-min Starkregen (T=1a)",
        "unit": "mm",
        "duration_min": 60,
        "return_period_a": 1,
        "buyer_text": "Fast jährliches Sommer-Ereignis - Bemessung Standard-Entwässerung",
    },
    "d60min_t10a": {
        "glob_default": "*D60*T10a*.tif",
        "label": "60-min Starkregen (T=10a)",
        "unit": "mm",
        "duration_min": 60,
        "return_period_a": 10,
        "buyer_text": "Sommergewitter, alle 10 Jahre - Hangentwässerung sollte das schaffen",
    },
    "d60min_t100a": {
        "glob_default": "*D60*T100a*.tif",
        "label": "60-min Starkregen (T=100a)",
        "unit": "mm",
        "duration_min": 60,
        "return_period_a": 100,
        "buyer_text": "Jahrhundert-Sommerregen - relevant für Keller, Garten-Mulden",
    },
    # 24h-Niederschlag (Tagesregen-Spektrum)
    "d24h_t1a": {
        "glob_default": "*D1440*T1a*.tif",
        "label": "24-h Niederschlag (T=1a)",
        "unit": "mm",
        "duration_min": 1440,
        "return_period_a": 1,
        "buyer_text": "Üblicher kräftiger Tagesregen - jährlich zu erwarten",
    },
    "d24h_t10a": {
        "glob_default": "*D1440*T10a*.tif",
        "label": "24-h Niederschlag (T=10a)",
        "unit": "mm",
        "duration_min": 1440,
        "return_period_a": 10,
        "buyer_text": "Vergleichsmaß - relativ häufiges 24-h-Ereignis",
    },
    "d24h_t100a": {
        "glob_default": "*D1440*T100a*.tif",
        "label": "24-h Niederschlag (T=100a)",
        "unit": "mm",
        "duration_min": 1440,
        "return_period_a": 100,
        "buyer_text": "Jahrhundert-Tageshochwasser - maßgebend für Bauplanung",
    },
}


class KostraLoader:
    """Singleton loader for the KOSTRA rasters in ``RASTER_DIR``.

    Use ``KostraLoader.get()`` from request handlers; the first call
    walks the directory and opens whichever rasters are present, the
    rest are cheap (single dict lookup).
    """

    _instance: "KostraLoader | None" = None

    @classmethod
    def get(cls) -> "KostraLoader":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._load()
        return cls._instance

    def __init__(self) -> None:
        self.slots: dict[str, RasterLookup] = {}
        self.base_dir: Path = Path(RASTER_DIR) / KOSTRA_SUBDIR
        self.available: bool = False

    def _load(self) -> None:
        if not self.base_dir.is_dir():
            logger.info(
                "KOSTRA dir %s not present — query() will return empty slots",
                self.base_dir,
            )
            return

        for slot_name, meta in KOSTRA_SLOTS.items():
            env_override = os.getenv(f"KOSTRA_{slot_name.upper()}_GLOB")
            pattern = env_override or meta["glob_default"]
            matches = sorted(self.base_dir.glob(pattern))
            if not matches:
                logger.info(
                    "KOSTRA slot %r: no file matched glob %r in %s",
                    slot_name, pattern, self.base_dir,
                )
                continue
            chosen = matches[0]
            try:
                lookup = RasterLookup(path=chosen)
                lookup.open()
                self.slots[slot_name] = lookup
                logger.info("KOSTRA slot %r: loaded %s", slot_name, chosen)
            except Exception:
                logger.exception(
                    "KOSTRA slot %r: failed to open %s — skipping",
                    slot_name, chosen,
                )

        self.available = bool(self.slots)

    def query(self, lat: float, lon: float) -> dict[str, Any]:
        """Return per-slot rainfall values for the given point.

        Schema::

            {
                "available": bool,         # any raster loaded at all?
                "attribution": str,
                "slots": {
                    "<slot_name>": {
                        "label": str,
                        "unit": str,
                        "buyer_text": str,
                        "value": float | None,   # None if NODATA or not loaded
                    },
                    ...
                },
            }

        ``value`` is ``None`` if the raster is missing or returns NODATA
        for the point — the report template renders "Daten in
        Vorbereitung" for missing slots and a numeric value otherwise.
        """
        out: dict[str, Any] = {
            "available": self.available,
            "attribution": ATTRIBUTION,
            "slots": {},
        }
        for slot_name, meta in KOSTRA_SLOTS.items():
            entry = {
                "label": meta["label"],
                "unit": meta["unit"],
                "buyer_text": meta["buyer_text"],
                "duration_min": meta.get("duration_min"),
                "return_period_a": meta.get("return_period_a"),
                "value": None,
            }
            lookup = self.slots.get(slot_name)
            if lookup is not None:
                try:
                    raw = lookup.query(lat, lon)
                    if raw != _NODATA:
                        entry["value"] = float(raw)
                except Exception:
                    logger.exception(
                        "KOSTRA slot %r query failed for (%s, %s)",
                        slot_name, lat, lon,
                    )
            out["slots"][slot_name] = entry
        return out
