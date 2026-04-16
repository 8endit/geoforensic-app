"""Pre-load soil raster and tabular datasets for fast local lookups.

Ported from ProofTrailAgents/geoforensic/backend/reports/preloader.py.
Loads SoilGrids GeoTIFFs, LUCAS CSV, and CORINE from F:\ (or configurable dir).
Point queries run in microseconds after initial load.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

RASTER_DIR = os.getenv("RASTER_DIR", "F:/jarvis-eye-data/geoforensic-rasters")
_NODATA = -999.0
_METAL_COLS = ["Cd", "Pb", "Hg", "As", "Cr", "Cu", "Ni", "Zn"]

# BBodSchV Vorsorgewerte (mg/kg) for comparison in reports
BBODSCHV_VORSORGE = {
    "Cd": 1.0, "Pb": 70.0, "Hg": 0.5, "As": 20.0,
    "Cr": 60.0, "Cu": 40.0, "Ni": 50.0, "Zn": 150.0,
}

SOILGRIDS_PROPERTIES = {
    "soc": {"file": "soilgrids_soc_0-30cm.tif", "scale": 0.1, "unit": "g/kg", "label": "Org. Kohlenstoff (SOC)"},
    "phh2o": {"file": "soilgrids_phh2o_0-30cm.tif", "scale": 0.1, "unit": "pH", "label": "pH-Wert"},
    "bdod": {"file": "soilgrids_bdod_0-30cm.tif", "scale": 0.01, "unit": "g/cm³", "label": "Lagerungsdichte"},
    "clay": {"file": "soilgrids_clay_0-30cm.tif", "scale": 0.1, "unit": "%", "label": "Tongehalt"},
    "sand": {"file": "soilgrids_sand_0-30cm.tif", "scale": 0.1, "unit": "%", "label": "Sandgehalt"},
    "silt": {"file": "soilgrids_silt_0-30cm.tif", "scale": 0.1, "unit": "%", "label": "Schluffgehalt"},
}

CLC_LABELS = {
    111: "Durchgängig städtische Prägung", 112: "Nicht durchgängig städtische Prägung",
    121: "Industrie- und Gewerbeflächen", 122: "Straßen-/Eisenbahnnetze",
    131: "Abbauflächen", 133: "Baustellen", 141: "Städtische Grünflächen",
    142: "Sport- und Freizeitanlagen", 211: "Nicht bewässertes Ackerland",
    221: "Weinbauflächen", 222: "Obst-/Beerenobstbestände",
    231: "Wiesen und Weiden", 242: "Komplexe Parzellenstrukturen",
    243: "Landw. + natürliche Vegetation", 311: "Laubwälder",
    312: "Nadelwälder", 313: "Mischwälder", 321: "Natürliches Grünland",
    324: "Wald-Strauch-Übergangsstadien", 411: "Sümpfe",
    511: "Gewässerläufe", 512: "Wasserflächen",
}

# Risk flags for land use
CLC_RISK_CODES = {121, 122, 131, 133}  # Industrial/mining → potential contamination


@dataclass
class RasterLookup:
    """Memory-mapped GeoTIFF with fast point queries."""
    path: Path
    _ds: object = field(default=None, repr=False)

    def open(self) -> None:
        import rasterio
        self._ds = rasterio.open(str(self.path))

    def query(self, lat: float, lon: float, search_radius: int = 5) -> float:
        if self._ds is None:
            return _NODATA
        try:
            row, col = self._ds.index(lon, lat)
            data = self._ds.read(1)
            h, w = data.shape
            nodata = self._ds.nodata

            def _valid(v):
                return (nodata is None or v != nodata) and v != 0

            if 0 <= row < h and 0 <= col < w:
                val = data[row, col]
                if _valid(val):
                    return float(val)

            for r in range(1, search_radius + 1):
                for dr in range(-r, r + 1):
                    for dc in range(-r, r + 1):
                        if abs(dr) != r and abs(dc) != r:
                            continue
                        rr, cc = row + dr, col + dc
                        if 0 <= rr < h and 0 <= cc < w:
                            val = data[rr, cc]
                            if _valid(val):
                                return float(val)
            return _NODATA
        except Exception:
            return _NODATA

    def close(self) -> None:
        if self._ds:
            self._ds.close()
            self._ds = None


@dataclass
class LucasLookup:
    """KD-tree nearest-neighbor lookup for LUCAS heavy metals + nutrients."""
    path: Path
    _tree: object = field(default=None, repr=False)
    _df: object = field(default=None, repr=False)

    def load(self) -> None:
        import pandas as pd
        from scipy.spatial import cKDTree

        df = pd.read_csv(str(self.path))
        df.columns = [c.strip() for c in df.columns]
        lat_col = next((c for c in df.columns if c.lower() in ("lat", "latitude")), None)
        lon_col = next((c for c in df.columns if c.lower() in ("lon", "longitude")), None)
        if not lat_col or not lon_col:
            return
        df = df.rename(columns={lat_col: "lat", lon_col: "lon"}).dropna(subset=["lat", "lon"])
        self._tree = cKDTree(df[["lat", "lon"]].values)
        self._df = df

    def query_metals(self, lat: float, lon: float, k: int = 3) -> dict:
        if self._tree is None or self._df is None:
            return {}
        dists, idxs = self._tree.query([lat, lon], k=k)
        if np.isscalar(dists):
            dists, idxs = [dists], [idxs]
        result = {}
        for metal in _METAL_COLS:
            if metal not in self._df.columns:
                continue
            vals, weights = [], []
            for d, i in zip(dists, idxs):
                v = self._df.iloc[i].get(metal)
                if v is not None and not np.isnan(v):
                    vals.append(float(v))
                    weights.append(1.0 / max(d, 0.001))
            if vals:
                tw = sum(weights)
                result[metal] = round(sum(v * w for v, w in zip(vals, weights)) / tw, 2)
        return result

    def query_nutrients(self, lat: float, lon: float, k: int = 3) -> dict:
        if self._tree is None or self._df is None:
            return {}
        dists, idxs = self._tree.query([lat, lon], k=k)
        if np.isscalar(dists):
            dists, idxs = [dists], [idxs]
        result = {}
        for col in ["P", "N_total"]:
            if col not in self._df.columns:
                continue
            vals, weights = [], []
            for d, i in zip(dists, idxs):
                v = self._df.iloc[i].get(col)
                if v is not None and not np.isnan(v):
                    vals.append(float(v))
                    weights.append(1.0 / max(d, 0.001))
            if vals:
                tw = sum(weights)
                result[col] = round(sum(v * w for v, w in zip(vals, weights)) / tw, 2)
        return result

    def query_nearest_distance_km(self, lat: float, lon: float) -> float:
        if self._tree is None:
            return -1.0
        dist, _ = self._tree.query([lat, lon], k=1)
        return round(dist * 111.0, 1)  # rough deg→km


class SoilDataLoader:
    """Singleton holding all pre-loaded soil datasets."""

    _instance: SoilDataLoader | None = None

    def __init__(self, raster_dir: str | Path | None = None):
        self.raster_dir = Path(raster_dir or RASTER_DIR)
        self._soilgrids: dict[str, RasterLookup] = {}
        self._corine: Optional[RasterLookup] = None
        self._lucas: Optional[LucasLookup] = None
        self._loaded = False

    @classmethod
    def get(cls) -> SoilDataLoader:
        """Get or create the singleton instance."""
        if cls._instance is None or not cls._instance._loaded:
            cls._instance = cls()
            cls._instance.load()
        return cls._instance

    def load(self) -> SoilDataLoader:
        if not self.raster_dir.is_dir():
            logger.warning("Raster dir not found: %s", self.raster_dir)
            self._loaded = True
            return self

        for prop, meta in SOILGRIDS_PROPERTIES.items():
            path = self.raster_dir / meta["file"]
            if path.exists():
                rl = RasterLookup(path=path)
                rl.open()
                self._soilgrids[prop] = rl

        clc_path = self.raster_dir / "corine_2024_100m.tif"
        if clc_path.exists():
            self._corine = RasterLookup(path=clc_path)
            self._corine.open()

        lucas_path = self.raster_dir / "lucas_soil_de.csv"
        if lucas_path.exists():
            self._lucas = LucasLookup(path=lucas_path)
            self._lucas.load()

        self._loaded = True
        loaded = [f"soilgrids:{k}" for k in self._soilgrids]
        if self._corine:
            loaded.append("corine")
        if self._lucas:
            loaded.append("lucas")
        logger.info("SoilDataLoader ready: %s", ", ".join(loaded) or "no datasets")
        return self

    def query_soilgrids(self, lat: float, lon: float, prop: str) -> float | None:
        rl = self._soilgrids.get(prop)
        if rl is None:
            return None
        raw = rl.query(lat, lon)
        if raw == _NODATA:
            return None
        return round(raw * SOILGRIDS_PROPERTIES[prop]["scale"], 3)

    def query_all_soilgrids(self, lat: float, lon: float) -> dict[str, float | None]:
        return {prop: self.query_soilgrids(lat, lon, prop) for prop in SOILGRIDS_PROPERTIES}

    def query_corine(self, lat: float, lon: float) -> dict | None:
        if self._corine is None:
            return None
        val = self._corine.query(lat, lon)
        if val == _NODATA:
            return None
        code = int(val)
        if code in CLC_LABELS:
            return {"code": code, "label": CLC_LABELS[code], "risk": code in CLC_RISK_CODES}
        return None

    def query_metals(self, lat: float, lon: float) -> dict:
        if self._lucas is None:
            return {}
        return self._lucas.query_metals(lat, lon)

    def query_nutrients(self, lat: float, lon: float) -> dict:
        if self._lucas is None:
            return {}
        return self._lucas.query_nutrients(lat, lon)

    def query_lucas_distance_km(self, lat: float, lon: float) -> float:
        if self._lucas is None:
            return -1.0
        return self._lucas.query_nearest_distance_km(lat, lon)

    def query_full_profile(self, lat: float, lon: float) -> dict:
        """Run all queries and return a complete soil profile."""
        soil = self.query_all_soilgrids(lat, lon)
        metals = self.query_metals(lat, lon)
        nutrients = self.query_nutrients(lat, lon)
        corine = self.query_corine(lat, lon)
        lucas_dist = self.query_lucas_distance_km(lat, lon)

        # Compare metals to BBodSchV thresholds
        metal_status = {}
        for m, val in metals.items():
            threshold = BBODSCHV_VORSORGE.get(m)
            if threshold:
                metal_status[m] = {
                    "value": val,
                    "threshold": threshold,
                    "unit": "mg/kg",
                    "status": "ok" if val < threshold else ("warn" if val < threshold * 1.5 else "critical"),
                }

        return {
            "soilgrids": soil,
            "metals": metals,
            "metal_status": metal_status,
            "nutrients": nutrients,
            "corine": corine,
            "lucas_distance_km": lucas_dist,
        }
