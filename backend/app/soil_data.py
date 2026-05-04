"""Pre-load soil raster and tabular datasets for fast local lookups.

Ported from ProofTrailAgents/geoforensic/backend/reports/preloader.py and
extended for the geoforensic-app pipeline. Loads SoilGrids GeoTIFFs, LUCAS
CSV, CORINE 2018, HRL Imperviousness, and WRB soil classification from the
RASTER_DIR env var. Point queries run in microseconds after initial load.

Source provenance per dataset:
    SoilGrids 250m  — ISRIC/WSI, CC BY 4.0, https://soilgrids.org
    LUCAS Soil      — JRC ESDAC, EU Open Data, https://esdac.jrc.ec.europa.eu/
    CORINE 2018     — Copernicus EEA, CLC2018 v2020_20u1, 100m raster
                      Pixel values are 1-44 indices that map to CLC Level-3
                      codes 111-523 via CORINE_INDEX_TO_CODE below.
                      Falls Raster fehlt: OSM Overpass landuse fallback.
    HRL Imperv. 20m — Copernicus Land Monitoring Service, % surface sealing
    WRB Soil Class  — SoilGrids MostProbable WRB raster (codes 1-29)
                      Used to derive AWC via WRB_AWC_LOOKUP.
    BBodSchV-Werte  — Bundes-Bodenschutz-Verordnung §8 Anhang 2
"""

from __future__ import annotations

import logging
import math
import os
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

RASTER_DIR = os.getenv("RASTER_DIR", "/app/rasters")
_NODATA = -999.0
_METAL_COLS = ["Cd", "Pb", "Hg", "As", "Cr", "Cu", "Ni", "Zn"]

# ── Heavy-metal soil thresholds — country-specific ─────────────────────────

# Germany — BBodSchV §8 Anhang 2, Lehm/Schluff (mg/kg)
BBODSCHV_VORSORGE = {
    "Cd": 1.0, "Pb": 70.0, "Hg": 0.5, "As": 20.0,
    "Cr": 60.0, "Cu": 40.0, "Ni": 50.0, "Zn": 150.0,
}
BBODSCHV_MASSNAHME = {
    "Cd": 20.0, "Pb": 400.0, "Hg": 10.0, "As": 50.0,
    "Cr": 200.0, "Cu": 200.0, "Ni": 200.0, "Zn": 600.0,
}

# Netherlands — Circulaire bodemsanering 2013, Bijlage 1
# Standaardbodem 25 % lutum, 10 % organische stof (mg/kg).
# Streefwaarde = niveau zonder noemenswaardige risico's (≈ "Vorsorge")
# Interventiewaarde = ernstig vervuilingscase, sanering vereist (≈ "Maßnahme")
NL_STREEFWAARDE = {
    "Cd": 0.8, "Pb": 85.0, "Hg": 0.3, "As": 29.0,
    "Cr": 100.0, "Cu": 36.0, "Ni": 35.0, "Zn": 140.0,
}
NL_INTERVENTIEWAARDE = {
    "Cd": 12.0, "Pb": 530.0, "Hg": 36.0, "As": 55.0,
    "Cr": 380.0, "Cu": 190.0, "Ni": 210.0, "Zn": 720.0,
}

# Country → (lower threshold, upper threshold, label-of-lower, label-of-upper, source)
METAL_THRESHOLDS = {
    "de": {
        "lower": BBODSCHV_VORSORGE,
        "upper": BBODSCHV_MASSNAHME,
        "lower_label": "Vorsorgewert",
        "upper_label": "Maßnahmenwert",
        "source": "BBodSchV §8 Anhang 2 (Lehm/Schluff)",
    },
    "nl": {
        "lower": NL_STREEFWAARDE,
        "upper": NL_INTERVENTIEWAARDE,
        "lower_label": "Streefwaarde",
        "upper_label": "Interventiewaarde",
        "source": "Circulaire bodemsanering 2013, Bijlage 1 (standaardbodem 25 % lutum / 10 % o.s.)",
    },
}

# Default for AT/CH or unknown country: BBodSchV as conservative reference
def get_thresholds(country_code: str) -> dict:
    return METAL_THRESHOLDS.get(country_code.lower(), METAL_THRESHOLDS["de"])

# ── SoilGrids properties ───────────────────────────────────────────────────

SOILGRIDS_PROPERTIES = {
    "soc": {"file": "soilgrids_soc_0-30cm.tif", "scale": 0.1, "unit": "g/kg", "label": "Org. Kohlenstoff (SOC)"},
    "phh2o": {"file": "soilgrids_phh2o_0-30cm.tif", "scale": 0.1, "unit": "pH", "label": "pH-Wert"},
    "bdod": {"file": "soilgrids_bdod_0-30cm.tif", "scale": 0.01, "unit": "g/cm³", "label": "Lagerungsdichte"},
    "clay": {"file": "soilgrids_clay_0-30cm.tif", "scale": 0.1, "unit": "%", "label": "Tongehalt"},
    "sand": {"file": "soilgrids_sand_0-30cm.tif", "scale": 0.1, "unit": "%", "label": "Sandgehalt"},
    "silt": {"file": "soilgrids_silt_0-30cm.tif", "scale": 0.1, "unit": "%", "label": "Schluffgehalt"},
}

# ── WRB → AWC lookup ───────────────────────────────────────────────────────

# WRB MostProbable code (1-29 in our SoilGrids extract) → typical AWC mm/m.
# Derived from WRB 2015 Reference Soil Group texture characteristics + ISRIC
# water retention studies. Used as fallback when no direct AWC raster exists.
WRB_AWC_LOOKUP = {
    1: 120, 2: 100, 3: 180, 4: 160, 5: 140, 6: 170, 7: 130,
    8: 150, 9: 110, 10: 160, 11: 90, 12: 170, 13: 140, 14: 120,
    15: 100, 16: 150, 17: 130, 18: 160, 19: 80, 20: 140, 21: 130,
    22: 120, 23: 150, 24: 160, 25: 110, 26: 140, 27: 100, 28: 90, 29: 70,
}

# ── CORINE 2018 (CLC2018 v2020_20u1) — pixel index → CLC code ──────────────

# The Copernicus raster encodes Level-3 codes as 1-byte indices to keep file
# size down. The mapping below is the official ESRI VAT order (raster legend
# CLC2018_CLC2018_V2018_20_QGIS.txt). NoData = -128.
CORINE_INDEX_TO_CODE = {
    1: 111, 2: 112, 3: 121, 4: 122, 5: 123, 6: 124,
    7: 131, 8: 132, 9: 133,
    10: 141, 11: 142,
    12: 211, 13: 212, 14: 213,
    15: 221, 16: 222, 17: 223,
    18: 231,
    19: 241, 20: 242, 21: 243, 22: 244,
    23: 311, 24: 312, 25: 313,
    26: 321, 27: 322, 28: 323, 29: 324,
    30: 331, 31: 332, 32: 333, 33: 334, 34: 335,
    35: 411, 36: 412,
    37: 421, 38: 422, 39: 423,
    40: 511, 41: 512,
    42: 521, 43: 522, 44: 523,
}

# CLC code → German label (full Level-3 nomenclature)
CLC_LABELS = {
    111: "Durchgängig städtische Prägung",
    112: "Nicht durchgängig städtische Prägung",
    121: "Industrie- und Gewerbeflächen",
    122: "Straßen-/Eisenbahnnetze",
    123: "Hafengebiete",
    124: "Flughäfen",
    131: "Abbauflächen",
    132: "Deponien und Abraumhalden",
    133: "Baustellen",
    141: "Städtische Grünflächen",
    142: "Sport- und Freizeitanlagen",
    211: "Nicht bewässertes Ackerland",
    212: "Bewässertes Ackerland",
    213: "Reisfelder",
    221: "Weinbauflächen",
    222: "Obst-/Beerenobstbestände",
    223: "Olivenhaine",
    231: "Wiesen und Weiden",
    241: "Einjährige Kulturen + Dauerkulturen",
    242: "Komplexe Parzellenstrukturen",
    243: "Landw. + natürliche Vegetation",
    244: "Agro-Forstwirtschaft",
    311: "Laubwälder",
    312: "Nadelwälder",
    313: "Mischwälder",
    321: "Natürliches Grünland",
    322: "Heiden und Moorheiden",
    323: "Hartlaubvegetation",
    324: "Wald-Strauch-Übergangsstadien",
    331: "Strände, Dünen, Sandflächen",
    332: "Felsflächen ohne Vegetation",
    333: "Spärlich bewachsene Flächen",
    334: "Brandflächen",
    335: "Gletscher und Dauerschneegebiete",
    411: "Sümpfe",
    412: "Torfmoore",
    421: "Salzwiesen",
    422: "Salinen",
    423: "Wattflächen",
    511: "Gewässerläufe",
    512: "Wasserflächen",
    521: "Küstenlagunen",
    522: "Mündungsgebiete",
    523: "Meere und Ozeane",
}

# Codes that flag potential contamination / risk for our reports
CLC_RISK_CODES = {121, 122, 131, 132, 133}

# ── OSM Overpass fallback (when CORINE raster is missing or NoData) ────────

# OSM landuse / natural / leisure tag → CORINE Level-3 code mapping.
_OSM_TO_CLC: dict[str, int] = {
    # Built-up
    "residential": 112,
    "retail": 121, "commercial": 121, "industrial": 121, "garages": 121,
    "construction": 133, "railway": 122, "highway": 122,
    "port": 123, "quarry": 131, "landfill": 132, "brownfield": 133,
    "cemetery": 141, "recreation_ground": 142,
    "village_green": 141, "grass": 141, "park": 141, "garden": 141,
    # Agriculture
    "farmland": 211, "allotments": 242, "farmyard": 242,
    "orchard": 222, "vineyard": 221,
    "meadow": 231, "pasture": 231, "animal_keeping": 231,
    # Natural / forest
    "forest": 312,  # default conifer; refined by leaf_type below
    "wood": 313, "scrub": 322, "heath": 322,
    "grassland": 321, "fell": 333, "bare_rock": 332,
    "beach": 331, "sand": 331,
    # Water / wetland
    "wetland": 411, "marsh": 411, "bog": 412,
    "water": 512, "reservoir": 512, "basin": 512, "salt_pond": 422,
}

_OVERPASS_CACHE: dict[tuple[float, float], Optional[dict]] = {}


def _query_overpass_landuse(lat: float, lon: float, radius_m: int = 400) -> Optional[dict]:
    """Query OSM Overpass for the dominant landuse around (lat, lon).

    Returns ``{"code": int, "label": str, "source": "osm-overpass"}`` or
    ``None`` on any failure (timeout, network, no hits). 5-second timeout.
    """
    key = (round(lat, 4), round(lon, 4))
    if key in _OVERPASS_CACHE:
        return _OVERPASS_CACHE[key]

    try:
        import httpx
    except ImportError:
        return None

    q = (
        f"[out:json][timeout:4];"
        f"(way(around:{radius_m},{lat},{lon})[landuse];"
        f" way(around:{radius_m},{lat},{lon})[natural~'wood|water|wetland|scrub|heath|grassland|bare_rock|beach|sand'];"
        f" way(around:{radius_m},{lat},{lon})[leisure~'park|garden|recreation_ground'];);"
        f"out tags;"
    )
    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]
    elements: list[dict] = []
    for url in endpoints:
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.post(url, data={"data": q})
                if r.status_code == 200:
                    elements = r.json().get("elements", []) or []
                    break
        except Exception as e:  # noqa: BLE001
            logger.debug("Overpass %s failed: %s", url, e)
            continue

    if not elements:
        return None  # don't cache misses (could be transient 429)

    tally: Counter[str] = Counter()
    for el in elements:
        tags = el.get("tags") or {}
        if "landuse" in tags:
            tally[tags["landuse"]] += 3
        if "natural" in tags:
            tally[tags["natural"]] += 2
        if "leisure" in tags:
            tally[tags["leisure"]] += 1

    if not tally:
        return None

    for tag, _count in tally.most_common():
        code = _OSM_TO_CLC.get(tag)
        if code is None:
            continue
        if tag in ("forest", "wood"):
            for el in elements:
                lt = (el.get("tags") or {}).get("leaf_type")
                if lt == "broadleaved":
                    code = 311
                    break
                if lt == "mixed":
                    code = 313
                    break
        label = CLC_LABELS.get(code, f"CLC {code}")
        result = {"code": code, "label": label, "source": "osm-overpass",
                  "risk": code in CLC_RISK_CODES}
        _OVERPASS_CACHE[key] = result
        return result

    return None


# ── Raster lookup classes ──────────────────────────────────────────────────

@dataclass
class RasterLookup:
    """Memory-mapped GeoTIFF with fast point queries (with ring search)."""
    path: Path
    _ds: object = field(default=None, repr=False)

    def open(self) -> None:
        import rasterio
        self._ds = rasterio.open(str(self.path))

    def query(self, lat: float, lon: float, search_radius: int = 5) -> float:
        """Return raster value at (lat, lon). _NODATA on error.

        If the centre pixel is 0 or nodata, searches outward in concentric
        rings up to ``search_radius`` pixels for a valid value.
        """
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

    def query_window_mean(self, lat: float, lon: float, radius_m: int) -> Optional[float]:
        """Mean of valid pixels in a ±radius_m window. Returns None if all
        pixels are nodata/invalid or the window is outside the raster.

        Uses rasterio windowed read (does not load the full raster) — required
        for large rasters like HRL Imperviousness.
        """
        if self._ds is None:
            return None
        ds = self._ds

        try:
            row, col = ds.index(lon, lat)
            crs = ds.crs
            is_geographic = crs is not None and crs.is_geographic
        except Exception:
            return None

        px_x = abs(ds.transform.a) or 1.0
        px_y = abs(ds.transform.e) or px_x
        if is_geographic:
            m_per_deg_lat = 111_320.0
            m_per_deg_lon = 111_320.0 * max(0.01, math.cos(math.radians(lat)))
            px_x_m = px_x * m_per_deg_lon
            px_y_m = px_y * m_per_deg_lat
        else:
            px_x_m, px_y_m = px_x, px_y

        half_x = max(1, int(round(radius_m / max(px_x_m, 1e-6))))
        half_y = max(1, int(round(radius_m / max(px_y_m, 1e-6))))
        half = max(half_x, half_y)

        from rasterio.windows import Window
        h, w = ds.height, ds.width
        r0 = max(0, row - half)
        r1 = min(h, row + half + 1)
        c0 = max(0, col - half)
        c1 = min(w, col + half + 1)
        if r1 <= r0 or c1 <= c0:
            return None

        block = ds.read(1, window=Window(col_off=c0, row_off=r0,
                                         width=c1 - c0, height=r1 - r0))
        if block.size == 0:
            return None

        nodata = ds.nodata
        arr = block.astype("float32")
        mask = np.ones_like(arr, dtype=bool)
        if nodata is not None:
            mask &= arr != nodata
        # HRL: 254 = outside area, 255 = nodata. Treat anything outside [0,100] as invalid.
        mask &= (arr >= 0) & (arr <= 100)
        if not mask.any():
            return None
        return round(max(0.0, min(100.0, float(arr[mask].mean()))), 1)

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
        return round(dist * 111.0, 1)


# ── Singleton loader ───────────────────────────────────────────────────────

# CORINE filename: prefer reprojected DE+NL clip, fall back to legacy name.
_CORINE_FILENAME_CANDIDATES = [
    "corine_2018_clc_100m_de_nl.tif",  # reprojected from CLC2018 v2020_20u1
    "corine_2024_100m.tif",             # legacy (likely broken RGB rendering)
]
_HRL_IMPERVIOUS_FILENAME = "hrl_imperviousness_20m.tif"
_WRB_FILENAME = "soilhydro_awc_0-30cm.tif"  # mis-named on disk; contains WRB codes 1-29
_LUCAS_FILENAME = "lucas_soil_de.csv"

# ESDAC Soil Microbial Activity (Xu et al. 2020, JRC) — 1 km, EPSG:3035 LAEA.
# "lc" = land-cover-aware Modell (vorzuziehen über "gen" generic). Raster sind
# nativ in Meter-Projektion, nicht WGS84 — query_microbial() reprojiziert
# lat/lon zur Abfrage.
_MICROBIAL_DIR = "esdac_microbial/annual"
_MICROBIAL_CMIC_FILE = "Cmic_lc_annual_mean_t.tif.tif"   # ESDAC packt zwei .tif
_MICROBIAL_BAS_FILE = "bas_lc_annual_mean_t.tif"
_MICROBIAL_QO2_FILE = "qO2_annual_mean_lc.tif.tif"
_MICROBIAL_CRS = "EPSG:3035"


class SoilDataLoader:
    """Singleton holding all pre-loaded soil datasets."""

    _instance: SoilDataLoader | None = None

    def __init__(self, raster_dir: str | Path | None = None):
        self.raster_dir = Path(raster_dir or RASTER_DIR)
        self._soilgrids: dict[str, RasterLookup] = {}
        self._corine: Optional[RasterLookup] = None
        self._corine_uses_index_map: bool = False
        self._imperviousness: Optional[RasterLookup] = None
        self._wrb: Optional[RasterLookup] = None
        self._lucas: Optional[LucasLookup] = None
        # ESDAC microbial: drei separate Lookups (Cmic / bas / qO2). Wir
        # halten sie außerhalb von ._soilgrids, weil sie in EPSG:3035 leben
        # statt in WGS84 — query_microbial() macht die Transformation.
        self._microbial: dict[str, "RasterLookup"] = {}
        self._microbial_transformer = None  # lazily init via pyproj
        self._loaded = False

    @classmethod
    def get(cls) -> SoilDataLoader:
        if cls._instance is None or not cls._instance._loaded:
            cls._instance = cls()
            cls._instance.load()
        return cls._instance

    def load(self) -> SoilDataLoader:
        if not self.raster_dir.is_dir():
            logger.warning("Raster dir not found: %s", self.raster_dir)
            self._loaded = True
            return self

        # SoilGrids — prefer NL+DE extended raster if available
        for prop, meta in SOILGRIDS_PROPERTIES.items():
            base = meta["file"].replace(".tif", "")
            nlde_path = self.raster_dir / f"{base}_nlde.tif"
            orig_path = self.raster_dir / meta["file"]
            path = nlde_path if nlde_path.exists() else orig_path
            if path.exists():
                rl = RasterLookup(path=path)
                rl.open()
                self._soilgrids[prop] = rl

        # CORINE — try reprojected file first (Index→Code mapping), fall back
        # to legacy filename, fall back to Overpass at query time
        for fname in _CORINE_FILENAME_CANDIDATES:
            clc_path = self.raster_dir / fname
            if clc_path.exists():
                rl = RasterLookup(path=clc_path)
                rl.open()
                # Heuristic: if file is reprojected, pixel values are 1-44 indices.
                # Legacy file has 3-digit codes directly (or is RGB-broken).
                self._corine = rl
                self._corine_uses_index_map = (fname == "corine_2018_clc_100m_de_nl.tif")
                logger.info("Loaded CORINE: %s (index_map=%s)",
                            clc_path, self._corine_uses_index_map)
                break

        # HRL Imperviousness
        imp_path = self.raster_dir / _HRL_IMPERVIOUS_FILENAME
        if imp_path.exists():
            self._imperviousness = RasterLookup(path=imp_path)
            self._imperviousness.open()

        # WRB Soil Class (file is named "awc" but contains WRB codes 1-29)
        wrb_path = self.raster_dir / _WRB_FILENAME
        if wrb_path.exists():
            self._wrb = RasterLookup(path=wrb_path)
            self._wrb.open()

        # LUCAS soil (DE points; for NL we report distance and decline data)
        lucas_path = self.raster_dir / _LUCAS_FILENAME
        if lucas_path.exists():
            self._lucas = LucasLookup(path=lucas_path)
            self._lucas.load()

        # ESDAC Soil Microbial Activity (3 layers, EPSG:3035 native).
        microbial_dir = self.raster_dir / _MICROBIAL_DIR
        if microbial_dir.is_dir():
            for slot, fname in (
                ("cmic", _MICROBIAL_CMIC_FILE),
                ("bas", _MICROBIAL_BAS_FILE),
                ("qo2", _MICROBIAL_QO2_FILE),
            ):
                p = microbial_dir / fname
                if p.exists():
                    rl = RasterLookup(path=p)
                    rl.open()
                    self._microbial[slot] = rl
            if self._microbial:
                logger.info(
                    "Loaded ESDAC microbial layers: %s",
                    ", ".join(self._microbial),
                )

        self._loaded = True
        loaded = [f"soilgrids:{k}" for k in self._soilgrids]
        if self._corine:
            loaded.append("corine")
        if self._imperviousness:
            loaded.append("imperviousness")
        if self._wrb:
            loaded.append("wrb")
        if self._lucas:
            loaded.append("lucas")
        if self._microbial:
            loaded.append(f"microbial({len(self._microbial)})")
        logger.info("SoilDataLoader ready: %s", ", ".join(loaded) or "no datasets")
        return self

    # ── ESDAC microbial query (EPSG:3035 with on-the-fly reprojection) ─

    def query_microbial(self, lat: float, lon: float) -> dict[str, float | None] | None:
        """Sample Cmic / bas / qO2 from ESDAC microbial rasters at (lat, lon).

        Returns ``None`` if no rasters loaded. Returns a dict with keys
        cmic / bas / qo2 (each ``float | None``) when at least one layer
        responds. Raster CRS ist EPSG:3035 (LAEA Europe in Metern), wir
        reprojizieren das WGS84-Eingabepaar einmalig pro Aufruf.

        Units (per Xu et al. 2020):
          cmic — μg C / g Boden (mikrobielle Biomasse)
          bas  — μg CO2-C / g · h (basale Atmungsrate)
          qo2  — μg CO2-C / mg Cmic · h (metabolic quotient, Stress-Indikator)
        """
        if not self._microbial:
            return None
        if self._microbial_transformer is None:
            try:
                from pyproj import Transformer
                self._microbial_transformer = Transformer.from_crs(
                    "EPSG:4326", _MICROBIAL_CRS, always_xy=True,
                )
            except Exception as exc:
                logger.warning("pyproj unavailable for microbial reproject: %s", exc)
                return None

        try:
            x, y = self._microbial_transformer.transform(lon, lat)
        except Exception as exc:
            logger.warning("microbial reproject failed at (%s, %s): %s", lat, lon, exc)
            return None

        out: dict[str, float | None] = {"cmic": None, "bas": None, "qo2": None}
        for slot, rl in self._microbial.items():
            try:
                ds = rl._ds
                row, col = ds.index(x, y)
                h, w = ds.height, ds.width
                if not (0 <= row < h and 0 <= col < w):
                    continue
                # Windowed read so we don't load the whole raster
                from rasterio.windows import Window
                win = Window(col, row, 1, 1)
                arr = ds.read(1, window=win)
                if arr.size == 0:
                    continue
                val = float(arr[0, 0])
                nodata = ds.nodata
                if nodata is not None and val == nodata:
                    continue
                # ESDAC nodata sentinel is a tiny negative float — guard against it
                if val < -1e30:
                    continue
                out[slot] = round(val, 3)
            except Exception as exc:
                logger.warning("microbial query %s at (%s, %s) failed: %s", slot, lat, lon, exc)
        return out

    # ── Query methods ──────────────────────────────────────────────────

    def query_soilgrids(self, lat: float, lon: float, prop: str) -> float | None:
        rl = self._soilgrids.get(prop)
        if rl is None:
            return None
        raw = rl.query(lat, lon, search_radius=15)
        if raw == _NODATA:
            return None
        return round(raw * SOILGRIDS_PROPERTIES[prop]["scale"], 3)

    def query_all_soilgrids(self, lat: float, lon: float) -> dict[str, float | None]:
        return {prop: self.query_soilgrids(lat, lon, prop) for prop in SOILGRIDS_PROPERTIES}

    def query_corine(self, lat: float, lon: float) -> dict | None:
        """Return CORINE land cover at (lat, lon) with code, label, source.

        Tries the local raster first; if unavailable or NoData, falls back to
        OSM Overpass landuse so urban addresses still get a sensible value.
        """
        if self._corine is not None:
            val = self._corine.query(lat, lon, search_radius=3)
            if val != _NODATA:
                if self._corine_uses_index_map:
                    code = CORINE_INDEX_TO_CODE.get(int(val))
                else:
                    code = int(val) if 111 <= int(val) <= 523 else None
                if code in CLC_LABELS:
                    return {
                        "code": code,
                        "label": CLC_LABELS[code],
                        "risk": code in CLC_RISK_CODES,
                        "source": "corine-2018",
                    }
                logger.debug(
                    "CORINE returned out-of-range value %s at (%.4f,%.4f); "
                    "falling back to Overpass", val, lat, lon,
                )

        return _query_overpass_landuse(lat, lon)

    def query_imperviousness(self, lat: float, lon: float, radius_m: int = 100) -> float | None:
        """Return HRL Imperviousness percent (0-100) as the mean of all valid
        pixels in a ±radius_m window. Avoids single-pixel artefacts on roof/
        street centroids of geocoded points.
        """
        if self._imperviousness is None:
            return None
        if radius_m and radius_m > 0:
            try:
                m = self._imperviousness.query_window_mean(lat, lon, radius_m)
                if m is not None:
                    return m
            except Exception as e:  # noqa: BLE001
                logger.warning("Imperviousness window query failed: %s", e)
        # Fallback to single-pixel ring search
        val = self._imperviousness.query(lat, lon, search_radius=5)
        return None if val == _NODATA else round(float(val), 1)

    def query_wrb(self, lat: float, lon: float) -> int | None:
        """Return WRB Most-Probable soil class code (1-29), or None."""
        if self._wrb is None:
            return None
        val = self._wrb.query(lat, lon, search_radius=10)
        if val == _NODATA or val <= 0:
            return None
        return int(val)

    def query_awc(self, lat: float, lon: float) -> int | None:
        """Available Water Capacity (mm/m) derived from WRB code via
        WRB_AWC_LOOKUP. Returns None if WRB raster is unavailable.
        """
        wrb = self.query_wrb(lat, lon)
        if wrb is None:
            return None
        return WRB_AWC_LOOKUP.get(wrb)

    def query_metals(self, lat: float, lon: float, country_code: str = "de",
                     max_distance_km: float = 50.0) -> dict:
        """LUCAS heavy-metal IDW lookup.

        Hard country gate: our LUCAS CSV only contains DE points. For NL/AT/CH
        addresses the nearest DE point is typically >100 km away — returning
        IDW-interpolated values from there would be misleading. We honor the
        ``country_code`` and the ``max_distance_km`` cap and return ``{}``
        with the distance flagged elsewhere.
        """
        if self._lucas is None:
            return {}
        if country_code.lower() != "de":
            return {}
        dist_km = self._lucas.query_nearest_distance_km(lat, lon)
        if dist_km > max_distance_km:
            logger.debug("LUCAS nearest point %s km > cap %s — skipping metals",
                         dist_km, max_distance_km)
            return {}
        return self._lucas.query_metals(lat, lon)

    def query_nutrients(self, lat: float, lon: float, country_code: str = "de",
                        max_distance_km: float = 50.0) -> dict:
        if self._lucas is None:
            return {}
        if country_code.lower() != "de":
            return {}
        dist_km = self._lucas.query_nearest_distance_km(lat, lon)
        if dist_km > max_distance_km:
            return {}
        return self._lucas.query_nutrients(lat, lon)

    def query_lucas_distance_km(self, lat: float, lon: float) -> float:
        if self._lucas is None:
            return -1.0
        return self._lucas.query_nearest_distance_km(lat, lon)

    def query_full_profile(self, lat: float, lon: float, country_code: str = "de") -> dict:
        """Run all queries and return a complete soil profile."""
        soil = self.query_all_soilgrids(lat, lon)
        metals = self.query_metals(lat, lon, country_code=country_code)
        nutrients = self.query_nutrients(lat, lon, country_code=country_code)
        corine = self.query_corine(lat, lon)
        imperv = self.query_imperviousness(lat, lon)
        awc = self.query_awc(lat, lon)
        lucas_dist = self.query_lucas_distance_km(lat, lon)

        thr = get_thresholds(country_code)
        metal_status = {}
        for m, val in metals.items():
            lower = thr["lower"].get(m)
            upper = thr["upper"].get(m, (lower or 0) * 5)
            if lower:
                metal_status[m] = {
                    "value": val,
                    "lower_threshold": lower,
                    "upper_threshold": upper,
                    "lower_label": thr["lower_label"],
                    "upper_label": thr["upper_label"],
                    "unit": "mg/kg",
                    "source": thr["source"],
                    "status": ("ok" if val < lower
                               else ("warn" if val < upper else "critical")),
                }

        return {
            "soilgrids": soil,
            "metals": metals,
            "metal_status": metal_status,
            "nutrients": nutrients,
            "corine": corine,
            "imperviousness_pct": imperv,
            "awc_mm_m": awc,
            "lucas_distance_km": lucas_dist,
            "country_code": country_code.lower(),
            "threshold_source": thr["source"],
        }
