"""LUCAS Pesticides — NUTS2-aggregated detection data for 118 substances.

Source:
    LUCAS Topsoil Survey 2018 — Pesticide residues report,
    JRC Soil Observatory / ESDAC,
    https://esdac.jrc.ec.europa.eu/projects/lucas (LUCAS_Pesticides_dataset_2018)
    Data is aggregated to NUTS2 region level — concentrations are regional
    means (mg/kg) of detected residues, not point measurements.

Spatial lookup:
    NUTS 2021 polygons from Eurostat GISCO,
    https://gisco-services.ec.europa.eu/distribution/v2/nuts/

Honesty constraint:
    Concentrations are NUTS2-level means and represent a regional baseline,
    not the specific address. The PDF must label the section accordingly:
    "Regionaler Pestizid-Befund (NUTS2-Gebiet)" — not "Ihr Grundstück".

    BBodSchV has no Vorsorgewerte for the modern actives in this list.
    EU drinking-water threshold (0.1 µg/L per substance / 0.5 µg/L sum) is
    a water-quality limit, not directly applicable to soil — referenced in
    the report only as scale-of-magnitude context.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

RASTER_DIR = os.getenv("RASTER_DIR", "/app/rasters")

_PESTICIDES_FILE = "lucas_pesticides_nuts2.xlsx"
_NUTS2_GEOJSON = "nuts2_eu_2021.geojson"

# Excel layout: row 0 has the pesticide names ("Chemical Name", "2,4-DB", ...),
# rows 1-5 are CAS / LOQ / Unit / Media / "Average of …" sub-headers, then
# data starts at row 6.
_PESTICIDE_HEADER_ROW = 0
_PESTICIDE_SKIP_ROWS = list(range(1, 6))

# Substances of high regulatory interest (banned in EU but still detected
# in soils due to legacy persistence, or actively restricted)
_FLAGGED_SUBSTANCES = {
    "DDT,p,p'-", "DDT,o,p'-", "DDE,p,p'-", "DDE,o,p'-",
    "DDD,p,p'-(TDE)", "DDD,o,p'-(TDE)",
    "Aldrin", "Dieldrin", "Endrin",
    "Chlordanecis-(alpha)", "Chlordanetrans-(gamma)", "Chlordecone",
    "Endosulfan,alpha-", "Endosulfan,beta-", "Endosulfan,sulphate",
    "Atrazine", "Atrazine-deisopropyl", "Atrazine-desethyl",
    "Diuron", "Carbofuran", "Chlorpyrifos", "Chlorpyrifos-methyl",
}


@dataclass
class PesticideHit:
    name: str
    concentration_mg_kg: float
    flagged_legacy: bool = False


@dataclass
class PesticidesResult:
    nuts2_code: Optional[str]
    nuts2_name: Optional[str]
    n_substances_detected: int
    top_substances: list[PesticideHit] = field(default_factory=list)
    flagged_count: int = 0
    available: bool = False
    note: Optional[str] = None

    def to_dict(self) -> dict:
        """Plain dict for Jinja-template consumption.

        Sums concentrations across all detected substances and surfaces
        the highest-conc substance name — those are the headline KPIs
        Section 10 (`section_10_pestizide.html`) renders.
        """
        total_residue = round(
            sum(h.concentration_mg_kg for h in self.top_substances), 4
        )
        top_name = self.top_substances[0].name if self.top_substances else None
        return {
            "available": self.available,
            "nuts2_code": self.nuts2_code,
            "nuts2_name": self.nuts2_name,
            "regional_scope": self.nuts2_name,
            "detected_count": self.n_substances_detected,
            "flagged_count": self.flagged_count,
            "total_residue_mg_per_kg": total_residue,
            "top_substance": top_name,
            "top_substances": [
                {
                    "name": h.name,
                    "concentration_mg_kg": h.concentration_mg_kg,
                    "flagged_legacy": h.flagged_legacy,
                }
                for h in self.top_substances
            ],
            "note": self.note,
        }


class PesticidesLookup:
    _instance: "PesticidesLookup | None" = None

    def __init__(self) -> None:
        self._features: list[tuple[str, str, object]] = []  # (nuts_id, name, shapely geom)
        self._df = None  # pandas DataFrame indexed by NUTS2 code
        self._loaded = False

    @classmethod
    def get(cls) -> "PesticidesLookup":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._try_load()
        return cls._instance

    def _try_load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        raster_dir = Path(RASTER_DIR)
        xlsx = raster_dir / _PESTICIDES_FILE
        gj = raster_dir / _NUTS2_GEOJSON

        if not xlsx.exists():
            logger.warning("LUCAS pesticides Excel not found: %s", xlsx)
            return
        if not gj.exists():
            logger.warning("NUTS2 GeoJSON not found: %s", gj)
            return

        try:
            from shapely.geometry import shape
            with open(gj, encoding="utf-8") as f:
                data = json.load(f)
            for feat in data["features"]:
                props = feat.get("properties") or {}
                if props.get("LEVL_CODE") != 2:
                    continue
                nid = props.get("NUTS_ID")
                name = props.get("NAME_LATN") or props.get("NUTS_NAME") or nid
                geom = shape(feat["geometry"])
                self._features.append((nid, name, geom))
            logger.info("Loaded %d NUTS2 polygons", len(self._features))
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to load NUTS2 polygons: %s", e)
            return

        try:
            import pandas as pd
            df = pd.read_excel(
                xlsx, sheet_name="NUTS2_conc_EU",
                header=_PESTICIDE_HEADER_ROW, skiprows=_PESTICIDE_SKIP_ROWS,
            )
            df = df.rename(columns={df.columns[0]: "NUTS2", df.columns[1]: "n_detected"})
            df = df.dropna(subset=["NUTS2"])
            df = df.set_index("NUTS2")
            self._df = df
            logger.info("Loaded LUCAS pesticides: %d NUTS2 regions, %d substances",
                        len(df), len(df.columns) - 1)
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to load pesticides Excel: %s", e)
            self._df = None

    def _find_nuts2(self, lat: float, lon: float) -> tuple[Optional[str], Optional[str]]:
        if not self._features:
            return None, None
        try:
            from shapely.geometry import Point
            p = Point(lon, lat)
            for nid, name, geom in self._features:
                # Cheap bbox test before full contains
                minx, miny, maxx, maxy = geom.bounds
                if not (minx <= lon <= maxx and miny <= lat <= maxy):
                    continue
                if geom.contains(p):
                    return nid, name
        except Exception as e:  # noqa: BLE001
            logger.debug("NUTS2 lookup failed: %s", e)
        return None, None

    def query(self, lat: float, lon: float, top_k: int = 5) -> PesticidesResult:
        # Wenn weder Polygone noch DataFrame geladen wurden, ist die Datei
        # nicht im Raster-Verzeichnis abgelegt — das ehrlich sagen statt
        # "Adresse außerhalb EU".
        if not self._features and self._df is None:
            return PesticidesResult(
                nuts2_code=None, nuts2_name=None,
                n_substances_detected=0, available=False,
                note="LUCAS-Pestizid-Datensatz auf diesem Server nicht installiert.",
            )

        nuts2, name = self._find_nuts2(lat, lon)
        if nuts2 is None:
            return PesticidesResult(
                nuts2_code=None, nuts2_name=None,
                n_substances_detected=0, available=False,
                note="Adresse außerhalb der EU-NUTS2-Abdeckung",
            )

        if self._df is None or nuts2 not in self._df.index:
            return PesticidesResult(
                nuts2_code=nuts2, nuts2_name=name,
                n_substances_detected=0, available=False,
                note=f"Keine LUCAS-Pestizid-Daten für NUTS2 {nuts2}",
            )

        row = self._df.loc[nuts2]
        n_detected = int(row.get("n_detected", 0)) if not _is_nan(row.get("n_detected")) else 0

        # Collect non-NaN concentrations across all 118 pesticide columns
        hits: list[PesticideHit] = []
        flagged = 0
        for col, val in row.items():
            if col == "n_detected":
                continue
            if _is_nan(val):
                continue
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            if v <= 0:
                continue
            is_flag = col in _FLAGGED_SUBSTANCES
            if is_flag:
                flagged += 1
            hits.append(PesticideHit(name=col, concentration_mg_kg=round(v, 4),
                                     flagged_legacy=is_flag))

        hits.sort(key=lambda h: (-1 if h.flagged_legacy else 0, -h.concentration_mg_kg))
        top = hits[:top_k]

        return PesticidesResult(
            nuts2_code=nuts2, nuts2_name=name,
            n_substances_detected=len(hits),
            top_substances=top, flagged_count=flagged,
            available=True,
            note=(
                "NUTS2-Mittelwerte aus LUCAS-Topsoil-Stichprobe (regional, nicht "
                "grundstücksspezifisch). Keine direkten Boden-Schwellenwerte in "
                "BBodSchV; EU-Trinkwasser-Schwelle 0,1 µg/L als Größenordnungs-Kontext."
            ),
        )


def _is_nan(v) -> bool:
    try:
        import math
        if v is None:
            return True
        return isinstance(v, float) and math.isnan(v)
    except Exception:
        return v is None


def query_pesticides(lat: float, lon: float, top_k: int = 5) -> PesticidesResult:
    """Convenience wrapper. Returns :class:`PesticidesResult`."""
    return PesticidesLookup.get().query(lat, lon, top_k)
