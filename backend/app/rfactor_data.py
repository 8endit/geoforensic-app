"""RUSLE R-factor (rainfall erosivity) lookup.

The R-factor in MJ·mm/(ha·h·yr) drives the rainfall component of the RUSLE
soil erosion model (A = R × K × LS × C × P).

Primary source — when the raster is on disk:
    ESDAC ``Rainfall Erosivity in the EU and Switzerland`` (Panagos et al. 2015,
    https://esdac.jrc.ec.europa.eu/content/rainfall-erosivity-european-union-and-switzerland)
    1 km grid, EPSG:3035, derived from 1 541 weather stations + REDES.
    Mean EU+CH = 722; Norddeutschland ≈ 50; Mediterran/Alpen > 1 000.

Fallback — when the raster is missing:
    Latitude-linear approximation calibrated for Germany. Crude but
    monotonic (south > north), bounded at sensible limits. Marked as
    ``source='lat-linear-approx'`` so the PDF can flag it explicitly.

Set ``RFACTOR_RASTER_FILE`` env var or drop the raster as
``$RASTER_DIR/esdac_rfactor_eu_1km.tif`` to switch to the precise source.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

RASTER_DIR = os.getenv("RASTER_DIR", "/app/rasters")
_RFACTOR_FILENAME = os.getenv("RFACTOR_RASTER_FILE", "esdac_rfactor_eu_1km.tif")


@dataclass
class RFactorResult:
    value: float                # MJ·mm/(ha·h·yr)
    source: str                 # "esdac-2015" or "lat-linear-approx"
    note: Optional[str] = None  # human-readable provenance for the PDF


class RFactorLookup:
    _instance: "RFactorLookup | None" = None

    def __init__(self) -> None:
        self._raster = None  # rasterio dataset (lazy import)
        self._raster_path: Optional[Path] = None
        self._tried_load = False

    @classmethod
    def get(cls) -> "RFactorLookup":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._try_load()
        return cls._instance

    def _try_load(self) -> None:
        if self._tried_load:
            return
        self._tried_load = True
        path = Path(RASTER_DIR) / _RFACTOR_FILENAME
        if not path.exists():
            logger.info("ESDAC R-factor raster not found at %s — using lat-linear fallback", path)
            return
        try:
            import rasterio
            self._raster = rasterio.open(str(path))
            self._raster_path = path
            logger.info("Loaded ESDAC R-factor: %s", path)
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to load R-factor raster %s: %s", path, e)
            self._raster = None

    def query(self, lat: float, lon: float, country_code: str = "de") -> RFactorResult:
        # Try precise raster first (works for any EU country once present)
        if self._raster is not None:
            try:
                from rasterio.warp import transform
                ds = self._raster
                xs, ys = transform("EPSG:4326", ds.crs, [lon], [lat])
                row, col = ds.index(xs[0], ys[0])
                if 0 <= row < ds.height and 0 <= col < ds.width:
                    val = ds.read(1, window=((row, row + 1), (col, col + 1)))
                    if val.size:
                        v = float(val[0, 0])
                        nodata = ds.nodata
                        if (nodata is None or v != nodata) and v > 0:
                            return RFactorResult(
                                value=round(v, 1),
                                source="esdac-2015",
                                note="ESDAC Rainfall Erosivity (Panagos 2015), 1 km",
                            )
            except Exception as e:  # noqa: BLE001
                logger.debug("R-factor raster query failed at (%s, %s): %s", lat, lon, e)

        # Fallback — country-specific linear approximation
        cc = country_code.lower()
        if cc == "de":
            # Norddt. (lat ~54°) ~50, Südbayern (lat ~47°) ~150, clamp [30, 200]
            approx = max(30.0, min(200.0, 150.0 - (lat - 47.0) * 14.3))
            note = "Breitengrad-Näherung DE (mangels ESDAC-Raster)"
        elif cc == "nl":
            # NL ist flach und niederschlagsmäßig homogen, typisch 50–80
            approx = 65.0
            note = "NL-Konstantnäherung (mangels ESDAC-Raster)"
        elif cc == "at":
            # AT mit Alpenanteil, höher als DE-Schnitt — 80 als grober Mittelwert
            approx = 100.0
            note = "AT-Konstantnäherung (mangels ESDAC-Raster)"
        elif cc == "ch":
            approx = 150.0
            note = "CH-Konstantnäherung Alpenraum (mangels ESDAC-Raster)"
        else:
            approx = 80.0
            note = f"Generische Näherung für {cc} (mangels ESDAC-Raster)"

        return RFactorResult(
            value=round(approx, 1),
            source="lat-linear-approx",
            note=note,
        )


def get_r_factor(lat: float, lon: float, country_code: str = "de") -> RFactorResult:
    """Convenience wrapper. Returns an :class:`RFactorResult`."""
    return RFactorLookup.get().query(lat, lon, country_code)
