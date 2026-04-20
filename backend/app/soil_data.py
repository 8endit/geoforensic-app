"""Pre-load soil raster and tabular datasets for fast local lookups.

Ported from ProofTrailAgents/geoforensic/backend/reports/preloader.py.
Loads SoilGrids GeoTIFFs, LUCAS CSV, and CORINE from RASTER_DIR env var.
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

RASTER_DIR = os.getenv("RASTER_DIR", "/app/rasters")
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


# DE state (ISO3166-2) → default NUTS2 code. Multi-NUTS2 states (BY/BW/NW)
# collapse to their capital/largest NUTS2 as a fallback when no polygon
# lookup is available. Replace with point-in-polygon against a NUTS2
# GeoJSON once one is shipped in RASTER_DIR/nuts2_de.geojson.
_STATE_TO_NUTS2_DEFAULT = {
    "DE-BE": "DE30", "DE-HH": "DE60", "DE-HB": "DE50",
    "DE-SH": "DEF0", "DE-SL": "DEC0", "DE-BB": "DE40",
    "DE-MV": "DE80", "DE-NI": "DE92", "DE-HE": "DE71",
    "DE-RP": "DEB1", "DE-SN": "DED2", "DE-ST": "DEE0",
    "DE-TH": "DEG0",
    "DE-BY": "DE21",  # Oberbayern
    "DE-BW": "DE11",  # Stuttgart
    "DE-NW": "DEA1",  # Düsseldorf
}


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


@dataclass
class PesticideLookup:
    """NUTS2-level pesticide concentration lookup from LUCAS Topsoil.

    Excel format assumed: first column is NUTS2 code (e.g. 'DE11'), remaining
    numeric columns are substance concentrations. Non-numeric columns after
    the NUTS2 one (e.g. region labels) are skipped. If the workbook shape
    differs, loading logs a warning and the feature stays silent instead of
    crashing.
    """
    path: Path
    _by_nuts2: dict[str, dict[str, float]] = field(default_factory=dict)
    _substances: list[str] = field(default_factory=list)
    _national_means: dict[str, float] = field(default_factory=dict)
    _national_p90: dict[str, float] = field(default_factory=dict)

    def load(self) -> None:
        import pandas as pd

        try:
            df = pd.read_excel(self.path)
        except Exception as exc:
            logger.warning("PesticideLookup: cannot read %s: %s", self.path, exc)
            return

        if df.empty or df.shape[1] < 2:
            logger.warning("PesticideLookup: empty or malformed workbook at %s", self.path)
            return

        # Find the NUTS2 code column. Preferred header names first, then
        # fall back to the first column that holds DE*-style strings.
        nuts_col = None
        for candidate in ("NUTS2", "nuts2", "NUTS_ID", "nuts_id", "NUTS2_CODE", "region"):
            if candidate in df.columns:
                nuts_col = candidate
                break
        if nuts_col is None:
            first = df.columns[0]
            if df[first].astype(str).str.match(r"^[A-Z]{2}[A-Z0-9]{1,3}$").any():
                nuts_col = first
        if nuts_col is None:
            logger.warning("PesticideLookup: no NUTS2 column detected in %s; columns=%s", self.path, list(df.columns)[:10])
            return

        numeric_cols = [c for c in df.columns if c != nuts_col and pd.api.types.is_numeric_dtype(df[c])]
        if not numeric_cols:
            logger.warning("PesticideLookup: no numeric substance columns found in %s", self.path)
            return

        self._substances = list(numeric_cols)
        for _, row in df.iterrows():
            code = str(row[nuts_col]).strip().upper()
            if not code.startswith("DE"):
                continue
            values = {c: float(row[c]) for c in numeric_cols if row[c] is not None and not pd.isna(row[c])}
            if values:
                self._by_nuts2[code] = values

        # National baselines for percentile framing in the report
        for c in numeric_cols:
            col_vals = df[c].dropna().astype(float)
            if len(col_vals) >= 3:
                self._national_means[c] = float(col_vals.mean())
                self._national_p90[c] = float(col_vals.quantile(0.9))

        logger.info("PesticideLookup: %d NUTS2 regions, %d substances from %s",
                    len(self._by_nuts2), len(self._substances), self.path.name)

    def available(self) -> bool:
        return bool(self._by_nuts2)

    def regions_loaded(self) -> int:
        return len(self._by_nuts2)

    def query(self, nuts2_code: str | None, top_n: int = 10) -> dict:
        """Return the top-N substances for a NUTS2 region plus regional context.

        Output shape:
            {
                "nuts2": "DE30",
                "top_substances": [{"name": str, "value_mg_kg": float, "percentile_national": int}, ...],
                "total_detected": int,
                "regional_percentile": int,   # where this region sits vs. DE-wide mean
            }
        """
        if not self._by_nuts2 or not nuts2_code:
            return {}
        row = self._by_nuts2.get(nuts2_code.upper())
        if row is None:
            return {}

        scored = []
        for name, val in row.items():
            p90 = self._national_p90.get(name)
            percentile = int(round(100 * val / p90)) if p90 and p90 > 0 else None
            scored.append({"name": name, "value_mg_kg": round(val, 4), "percentile_national": percentile})
        scored.sort(key=lambda x: x["value_mg_kg"], reverse=True)

        region_total = sum(row.values())
        regional_percentile = None
        national_sums = [sum(v.values()) for v in self._by_nuts2.values()]
        if national_sums:
            rank = sum(1 for s in national_sums if s <= region_total)
            regional_percentile = int(round(100 * rank / len(national_sums)))

        return {
            "nuts2": nuts2_code.upper(),
            "top_substances": scored[:top_n],
            "total_detected": len([v for v in row.values() if v > 0]),
            "regional_percentile": regional_percentile,
        }


class SoilDataLoader:
    """Singleton holding all pre-loaded soil datasets."""

    _instance: SoilDataLoader | None = None

    def __init__(self, raster_dir: str | Path | None = None):
        self.raster_dir = Path(raster_dir or RASTER_DIR)
        self._soilgrids: dict[str, RasterLookup] = {}
        self._corine: Optional[RasterLookup] = None
        self._lucas: Optional[LucasLookup] = None
        self._pesticides: Optional[PesticideLookup] = None
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
            # Prefer extended NL+DE raster if available
            base = meta["file"].replace(".tif", "")
            nlde_path = self.raster_dir / f"{base}_nlde.tif"
            orig_path = self.raster_dir / meta["file"]
            path = nlde_path if nlde_path.exists() else orig_path
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

        pesticides_path = self.raster_dir / "lucas_pesticides_nuts2.xlsx"
        if pesticides_path.exists():
            self._pesticides = PesticideLookup(path=pesticides_path)
            self._pesticides.load()
            if not self._pesticides.available():
                self._pesticides = None

        self._loaded = True
        loaded = [f"soilgrids:{k}" for k in self._soilgrids]
        if self._corine:
            loaded.append("corine")
        if self._lucas:
            loaded.append("lucas")
        if self._pesticides:
            loaded.append(f"pesticides({self._pesticides.regions_loaded()} NUTS2)")
        logger.info("SoilDataLoader ready: %s", ", ".join(loaded) or "no datasets")
        return self

    def query_soilgrids(self, lat: float, lon: float, prop: str) -> float | None:
        rl = self._soilgrids.get(prop)
        if rl is None:
            return None
        raw = rl.query(lat, lon, search_radius=15)  # 15px ~5km, covers urban areas
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

    def query_pesticides(self, nuts2_code: str | None) -> dict:
        """NUTS2-keyed pesticide regional context. Requires a NUTS2 code
        resolved upstream (typically from the geocoder response)."""
        if self._pesticides is None:
            return {}
        return self._pesticides.query(nuts2_code)

    def query_full_profile(self, lat: float, lon: float, state_iso: str | None = None) -> dict:
        """Run all queries and return a complete soil profile.

        `state_iso` is the ISO3166-2 state code (e.g. 'DE-BY') used to resolve
        the LUCAS pesticides NUTS2 lookup. When omitted, pesticide data is
        omitted from the profile.
        """
        soil = self.query_all_soilgrids(lat, lon)
        metals = self.query_metals(lat, lon)
        nutrients = self.query_nutrients(lat, lon)
        corine = self.query_corine(lat, lon)
        lucas_dist = self.query_lucas_distance_km(lat, lon)
        nuts2 = _STATE_TO_NUTS2_DEFAULT.get(state_iso.upper()) if state_iso else None
        pesticides = self.query_pesticides(nuts2)

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
            "pesticides": pesticides,
        }
