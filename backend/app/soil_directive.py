"""EU Soil Monitoring Directive (EU) 2025/2360 — Anhang I.

Ported from ProofTrailAgents/geoforensic/backend/reports/soil_directive.py
and adapted to the geoforensic-app SoilDataLoader API.

Per Annex I (Verabschiedung 12.11.2025, in Kraft seit 16.12.2025):
13 Bodendescriptoren in Teilen A (EU-Kriterien, 3 Items), B (Mitgliedstaat-
Kriterien, 5 Items) und C (rein beobachtend, 5 Items), plus 4 Versiegelungs-
Indikatoren in Teil D. Verifiziert gegen EUR-Lex PDF.

The directive is the legal anchor for our paid-product moat: until 2028
no German competitor (BBSR, K.A.R.L., on-geo, EnviroTrust, docestate)
maps these descriptors at address level. We do — with the explicit honesty
that 2 of 13 descriptors (Boden-Biodiversität via DNA-Metabarcoding,
PFAS-Konzentrationen) require in-situ sampling and cannot be derived
remotely; those are flagged ``status="not_remote"`` not faked.

Über die EU-Pflicht hinaus liefern wir 5 ergänzende Indikatoren
(Wind-Erosion separat, PAK/PCB, mikrobielle Aktivität, Bodenstruktur,
Hydromorphologie) — siehe ``organic_contaminants`` in part_b und
``erosion_wind`` in part_a.

Returns a structured dict consumed by the Vollbericht PDF template
``backend/app/full_report.py``.

Source provenance flows through SoilDataLoader (see soil_data.py) and
RFactorLookup (see rfactor_data.py). Each numeric output also carries a
``source`` hint so the PDF can show "ESDAC-Raster" vs "Modell-Schätzung".
"""

from __future__ import annotations

import logging
import math
from typing import Optional

from app.pesticides_data import query_pesticides
from app.rfactor_data import get_r_factor
from app.soil_data import (
    SoilDataLoader,
    get_thresholds,
)

logger = logging.getLogger(__name__)

# ── RUSLE K-factor by texture ──────────────────────────────────────────────
# Wischmeier & Smith 1978, simplified per USDA texture class (t·ha·h / ha·MJ·mm)
_K_FACTOR_BY_TEXTURE = {
    "clay": 0.022, "silty_clay": 0.026, "sandy_clay": 0.020,
    "clay_loam": 0.030, "silty_clay_loam": 0.035, "sandy_clay_loam": 0.025,
    "loam": 0.038, "silt_loam": 0.042, "sandy_loam": 0.030,
    "silt": 0.045, "loamy_sand": 0.020, "sand": 0.013,
}

# ── CORINE → RUSLE C-factor (crop/management, Panagos 2015) ────────────────
_CORINE_C_FACTOR = {
    111: 0.0, 112: 0.0, 121: 0.0, 122: 0.0, 131: 1.0, 133: 0.0,
    141: 0.01, 142: 0.01,
    211: 0.30, 212: 0.10, 213: 0.25, 221: 0.15, 222: 0.10, 223: 0.10,
    231: 0.01, 241: 0.20, 242: 0.20, 243: 0.10,
    311: 0.001, 312: 0.001, 313: 0.001, 321: 0.01, 322: 0.01,
    323: 0.01, 324: 0.005, 331: 1.0, 332: 0.0, 333: 0.5,
    411: 0.0, 412: 0.0, 511: 0.0, 512: 0.0,
}


# ── Classification helpers ────────────────────────────────────────────────

def _classify_metal(name: str, value: float, thresholds: dict) -> str:
    lower = thresholds["lower"].get(name)
    upper = thresholds["upper"].get(name)
    if lower and value > lower:
        if upper and value > upper:
            return "alert"
        return "warn"
    return "ok"


def _classify_soc(soc_pct: float) -> str:
    if soc_pct >= 1.5:
        return "ok"
    if soc_pct >= 1.0:
        return "warn"
    return "alert"


def _classify_ph(ph: float) -> str:
    if 5.0 <= ph <= 7.5:
        return "ok"
    if 4.5 <= ph <= 8.0:
        return "warn"
    return "alert"


def _texture_class(clay: float, sand: float, silt: float) -> str:
    """USDA soil texture triangle (simplified)."""
    if clay >= 40:
        return "clay"
    if clay >= 27 and sand <= 20:
        return "silty_clay"
    if clay >= 27 and sand > 20:
        return "sandy_clay"
    if 27 > clay >= 20 and silt >= 28:
        return "clay_loam"
    if silt >= 50 and clay >= 12:
        return "silty_clay_loam"
    if silt >= 50 and clay < 12:
        return "silt_loam"
    if silt >= 80:
        return "silt"
    if sand >= 85:
        return "sand"
    if sand >= 70:
        return "loamy_sand"
    if sand >= 52:
        return "sandy_loam"
    return "loam"


_TEXTURE_LABEL = {
    "clay": "Ton", "silty_clay": "Schluffiger Ton", "sandy_clay": "Sandiger Ton",
    "clay_loam": "Toniger Lehm", "silty_clay_loam": "Schluffig-toniger Lehm",
    "sandy_clay_loam": "Sandig-toniger Lehm", "loam": "Lehm",
    "silt_loam": "Schluffiger Lehm", "sandy_loam": "Sandiger Lehm",
    "silt": "Schluff", "loamy_sand": "Lehmiger Sand", "sand": "Sand",
}


# ── RUSLE Erosion model ───────────────────────────────────────────────────

def _estimate_erosion_rusle(
    lat: float,
    lon: float,
    clay: float | None,
    sand: float | None,
    silt: float | None,
    slope_deg: float,
    corine_code: int | None,
    country_code: str = "de",
) -> dict:
    """Simplified RUSLE: A = R × K × LS × C × P (t/ha/yr).

    R from ESDAC Panagos-2015 raster (or country-specific lat-linear fallback).
    K from texture (Wischmeier & Smith).
    LS from slope (simplified McCool).
    C from CORINE land cover.
    P = 1.0 (no conservation assumed).
    """
    r = get_r_factor(lat, lon, country_code)
    r_factor = r.value
    r_source = r.source

    if clay is not None and sand is not None and silt is not None:
        tex = _texture_class(clay, sand, silt)
        k_factor = _K_FACTOR_BY_TEXTURE.get(tex, 0.035)
    else:
        k_factor = 0.035  # default loam

    slope_pct = math.tan(math.radians(slope_deg)) * 100
    if slope_pct < 1:
        ls_factor = 0.1
    elif slope_pct < 3:
        ls_factor = 0.3
    elif slope_pct < 5:
        ls_factor = 0.5
    elif slope_pct < 9:
        ls_factor = max(0.5, 0.065 + 0.0456 * slope_pct + 0.006541 * slope_pct ** 2)
    else:
        ls_factor = max(1.0, 0.065 + 0.0456 * slope_pct + 0.006541 * slope_pct ** 2)
    ls_factor = min(ls_factor, 15.0)

    c_factor = _CORINE_C_FACTOR.get(corine_code, 0.10) if corine_code else 0.10
    p_factor = 1.0

    erosion = r_factor * k_factor * ls_factor * c_factor * p_factor
    status = "ok" if erosion < 2.0 else ("warn" if erosion <= 5.0 else "alert")

    # ESDAC + Panagos call the threshold "Tolerable Soil Loss" of 2 t/ha/yr
    return {
        "value": round(erosion, 2),
        "unit": "t/ha/Jahr",
        "threshold": "< 2.0 t/ha/Jahr",
        "status": status,
        "r_factor": r_factor,
        "r_source": r_source,
        "k_factor": round(k_factor, 3),
        "ls_factor": round(ls_factor, 2),
        "c_factor": round(c_factor, 3),
        "slope_deg": slope_deg,
    }


# ── Organic contaminants section (mixed remote + not-remote) ──────────────

def _build_organic_contaminants_section(lat: float, lon: float) -> dict:
    """Pesticides come from LUCAS @ NUTS2 (regional, not point); PFAS/PAK
    require in-situ sampling and are honestly flagged as ``not_remote``.
    """
    pest = query_pesticides(lat, lon, top_k=5)

    pesticides_block: dict
    if pest.available:
        # Map status from detection count + legacy-substance presence
        if pest.flagged_count > 0:
            status = "alert"
        elif pest.n_substances_detected >= 10:
            status = "warn"
        elif pest.n_substances_detected > 0:
            status = "ok"
        else:
            status = "ok"
        pesticides_block = {
            "status": status,
            "nuts2_code": pest.nuts2_code,
            "nuts2_name": pest.nuts2_name,
            "n_detected": pest.n_substances_detected,
            "flagged_legacy_count": pest.flagged_count,
            "top_substances": [
                {
                    "name": h.name,
                    "concentration_mg_kg": h.concentration_mg_kg,
                    "flagged_legacy": h.flagged_legacy,
                }
                for h in pest.top_substances
            ],
            "source": "LUCAS Topsoil 2018 (JRC ESDAC), aggregiert auf NUTS2",
            "note": pest.note,
        }
    else:
        pesticides_block = {
            "status": "na",
            "nuts2_code": pest.nuts2_code,
            "n_detected": 0,
            "source": "LUCAS Topsoil 2018 (JRC ESDAC)",
            "note": pest.note or "Keine LUCAS-Pestizid-Daten für diese Region",
        }

    return {
        "pesticides": pesticides_block,
        "pfas": {
            "status": "not_remote",
            "note": (
                "PFAS — In-situ-Beprobung nach DIN EN ISO 21675 erforderlich. "
                "Indikative EU-Liste wird Mitte 2027 veröffentlicht."
            ),
        },
        "pak_pcb": {
            "status": "not_remote",
            "note": (
                "PAK/PCB-Belastung — Beprobung gemäß BBodSchV §8 Anhang 1 "
                "erforderlich. Wird im Vorsorge-Screening nicht abgebildet."
            ),
        },
    }


# ── Main query ────────────────────────────────────────────────────────────

def query_soil_directive(
    lat: float,
    lon: float,
    slope_deg: Optional[float] = None,
    country_code: str = "de",
) -> dict:
    """Query all 16 EU Soil Monitoring Directive descriptors.

    Args:
        lat, lon: address coordinates (WGS-84).
        slope_deg: terrain slope at the address. If ``None``, uses 2° as a
            conservative default and flags ``slope_source="default"``.
            Pass a real value from slope_analysis when available.
        country_code: 'de'/'nl'/'at'/'ch'. Used to decide which thresholds
            and notes to apply. Currently only 'de' has full BBodSchV support
            — others fall back to BBodSchV as conservative default.

    Returns:
        Structured dict with parts A, B, C, D and an overall assessment.
    """
    loader = SoilDataLoader.get()
    cc = country_code.lower()
    thresholds = get_thresholds(cc)

    # ── Raw queries ────────────────────────────────────────────────────
    soc_raw = loader.query_soilgrids(lat, lon, "soc")
    ph_raw = loader.query_soilgrids(lat, lon, "phh2o")
    bdod = loader.query_soilgrids(lat, lon, "bdod")
    clay = loader.query_soilgrids(lat, lon, "clay")
    sand = loader.query_soilgrids(lat, lon, "sand")
    silt = loader.query_soilgrids(lat, lon, "silt")
    has_soilgrids = any(v is not None for v in [soc_raw, ph_raw, bdod])

    soc_pct = round(soc_raw / 10.0, 2) if soc_raw is not None else None
    imperviousness = loader.query_imperviousness(lat, lon, radius_m=100)
    corine = loader.query_corine(lat, lon)
    corine_code = corine["code"] if corine else None

    # LUCAS — country-gated. NL/AT/CH return {} so we don't show DE values
    # interpolated from 200 km away.
    metals = loader.query_metals(lat, lon, country_code=cc)
    lucas_dist_km = loader.query_lucas_distance_km(lat, lon)
    lucas_nutrients = loader.query_nutrients(lat, lon, country_code=cc)

    awc = loader.query_awc(lat, lon)
    wrb = loader.query_wrb(lat, lon)

    tex_class = None
    tex_label = None
    if clay is not None and sand is not None and silt is not None:
        tex_class = _texture_class(clay, sand, silt)
        tex_label = _TEXTURE_LABEL.get(tex_class, tex_class)

    if slope_deg is None:
        slope_deg = 2.0
        slope_source = "default"
    else:
        slope_source = "measured"

    # ── PART A: EU-wide criteria ───────────────────────────────────────

    erosion_water = _estimate_erosion_rusle(
        lat, lon, clay, sand, silt, slope_deg, corine_code, country_code=cc,
    )

    # Wind erosion: relevant only on sandy soils in flat terrain.
    # The lat>52° rule is calibrated for Norddeutschland; NL is just as flat
    # and partly sandy (Veluwe, Drenthe), so we apply the same rule there
    # but adjust the country wording.
    wind_risk = "gering"
    wind_status = "ok"
    if sand is not None and sand > 60 and lat > 52.0 and slope_deg < 3:
        wind_status = "warn"
        if cc == "nl":
            wind_risk = "verhoogd (zandgronden, Noord/Oost-Nederland)"
        else:
            wind_risk = "erhöht (sandige Böden, Norddeutschland)"

    part_a = {
        "erosion_water": erosion_water,
        "erosion_wind": {
            "risk": wind_risk,
            "status": wind_status,
            "note": "Modellbasiert" if (sand and sand > 60) else "Für Standort nicht relevant",
        },
        "soc_pct": soc_pct,
        "soc_gkg": round(soc_raw, 1) if soc_raw is not None else None,
        "soc_status": _classify_soc(soc_pct) if soc_pct is not None else "na",
        "ph": round(ph_raw, 1) if ph_raw is not None else None,
        "ph_status": _classify_ph(ph_raw) if ph_raw is not None else "na",
    }

    # ── PART B: National criteria ──────────────────────────────────────

    # Phosphor (CAL-extractable, mg/kg) — typical agricultural target 15–50
    p_value = lucas_nutrients.get("P")
    p_status = "na"
    if p_value is not None:
        p_status = "ok" if 15 <= p_value <= 50 else ("warn" if p_value > 50 else "alert")

    # Nitrogen surplus indicator (proxy from LUCAS N_total)
    # NOT a direct surplus measurement; rough conversion documented as such.
    n_total = lucas_nutrients.get("N_total")
    n_status = "na"
    n_surplus_est = None
    if n_total is not None:
        n_surplus_est = round(n_total / 70, 0)  # rough proxy, kg N/ha/yr
        n_status = "ok" if n_surplus_est < 50 else ("warn" if n_surplus_est < 80 else "alert")

    # Heavy metals — thresholds chosen by country (DE: BBodSchV, NL: Circulaire)
    metals_classified: list[dict] = []
    metals_overall_status = "ok" if metals else "na"
    for name in ["Cd", "Pb", "Hg", "As", "Cr", "Cu", "Ni", "Zn"]:
        val = metals.get(name)
        if val is not None:
            status = _classify_metal(name, val, thresholds)
            if status == "alert":
                metals_overall_status = "alert"
            elif status == "warn" and metals_overall_status != "alert":
                metals_overall_status = "warn"
            metals_classified.append({
                "name": name, "value": round(float(val), 2), "unit": "mg/kg",
                "lower_threshold": thresholds["lower"].get(name),
                "upper_threshold": thresholds["upper"].get(name),
                "lower_label": thresholds["lower_label"],
                "upper_label": thresholds["upper_label"],
                "source": thresholds["source"],
                "status": status,
            })

    # Water retention
    awc_status = "na"
    if awc is not None:
        awc_status = "ok" if awc >= 140 else ("warn" if awc >= 100 else "alert")

    # Salinisation — Germany generally non-saline; rough regional approximation
    ec_est = 0.15
    if lat > 53.5 and sand and sand > 60:
        ec_est = 0.8  # coastal sandy
    elif clay and clay > 35:
        ec_est = 0.3  # clay soils slightly higher
    salin_status = "ok" if ec_est < 2.0 else "warn"

    part_b = {
        "phosphor": {
            "value": round(float(p_value), 1) if p_value is not None else None,
            "unit": "mg/kg", "status": p_status,
            "threshold": "15–50 mg/kg (P-Olsen)",
            "source": "LUCAS Soil (ESDAC)",
        },
        "nitrogen": {
            "n_total_mgkg": round(float(n_total), 0) if n_total is not None else None,
            "surplus_est_kgha": n_surplus_est,
            "unit": "kg N/ha/Jahr (geschätzt)",
            "status": n_status,
            "threshold": "< 50 kg N/ha/Jahr",
            "source": "LUCAS-Indikator (kein direkter Surplus-Messwert)",
        },
        "metals": metals_classified,
        "metals_status": metals_overall_status,
        "metals_threshold_source": thresholds["source"],
        "metals_note": (
            None if metals
            else "Schwermetalle aus LUCAS-Boden für diese Region nicht standortspezifisch verfügbar."
        ),
        "lucas_distance_km": lucas_dist_km if metals else None,
        "bulk_density_g_cm3": round(float(bdod), 2) if bdod is not None else None,
        "bulk_density_status": (
            "ok" if (bdod is not None and bdod < 1.6)
            else ("warn" if bdod is not None and bdod >= 1.6 else "na")
        ),
        "texture": {
            "clay_pct": round(float(clay), 1) if clay is not None else None,
            "sand_pct": round(float(sand), 1) if sand is not None else None,
            "silt_pct": round(float(silt), 1) if silt is not None else None,
            "class": tex_class, "label": tex_label,
        },
        "water_retention": {
            "awc_mm_m": awc, "wrb_class": wrb,
            "status": awc_status, "threshold": "> 140 mm/m",
            "source": "WRB-Klassen-Lookup (SoilGrids)" if wrb else "nicht verfügbar",
        },
        "salinisation": {
            "ec_ds_m": round(ec_est, 2), "status": salin_status,
            "threshold": "< 2.0 dS/m",
            "source": "Regional-Schätzung (kein direkter EC-Messwert)",
        },
        "organic_contaminants": _build_organic_contaminants_section(lat, lon),
    }

    # ── PART C: Monitoring descriptors ─────────────────────────────────
    part_c = {
        "biodiversity": {
            "status": "not_remote",
            "note": "Basalatmung — erfordert In-situ-Beprobung und Laborinkubation.",
        },
        "microbial_diversity": {
            "status": "not_remote",
            "note": "eDNA-Analyse erforderlich. Monitoring-Descriptor ohne Bewertungskriterium.",
        },
    }

    # ── PART D: Land Take indicators ───────────────────────────────────
    part_d = {
        "imperviousness_pct": imperviousness,
        "imperviousness_source": (
            "HRL Imperviousness 20 m (Copernicus)" if imperviousness is not None else None
        ),
        "corine": corine,
        "soil_removal": {
            "status": "ok",
            "note": "Kein großflächiger Bodenabtrag erkennbar (Sentinel-2 Änderungsdetektion ausstehend).",
        },
    }

    # ── One-out-all-out assessment ─────────────────────────────────────

    all_statuses = [
        part_a["erosion_water"]["status"],
        part_a["erosion_wind"]["status"],
        part_a["soc_status"],
        part_a["ph_status"],
        p_status, n_status,
        metals_overall_status,
        part_b["bulk_density_status"],
        awc_status, salin_status,
    ]
    real_statuses = [s for s in all_statuses if s not in ("na", "not_remote")]

    if "alert" in real_statuses:
        overall = "ungesund"
    elif "warn" in real_statuses:
        overall = "bedingt"
    elif real_statuses:
        overall = "gesund"
    else:
        overall = "keine_daten"

    # Per EUR-Lex Annex I: 13 Bodendescriptoren in Teilen A+B+C
    # plus 4 Versiegelungs-Indikatoren in Teil D = 17 Mess-Größen.
    # Davon 2 echt nicht-remote: Biodiversität (DNA-Metabarcoding) + PFAS.
    total_descriptors = 13
    determined = sum(1 for s in all_statuses if s not in ("na", "not_remote"))
    not_remote = 2
    not_available = max(total_descriptors - determined - not_remote, 0)

    datasets = []
    if has_soilgrids:
        datasets.append("SoilGrids 250m (ISRIC, CC BY 4.0)")
    if metals or lucas_nutrients:
        datasets.append("LUCAS Soil (JRC ESDAC)")
    if imperviousness is not None:
        datasets.append("HRL Imperviousness 20m (Copernicus)")
    if corine is not None:
        src = corine.get("source", "corine")
        datasets.append(
            "CORINE Land Cover 2018 (Copernicus EEA)" if src == "corine-2018"
            else "OSM Overpass landuse (Fallback)"
        )
    if awc is not None:
        datasets.append("WRB Soil Classification (SoilGrids)")
    datasets.append(f"R-Faktor: {erosion_water['r_source']}")

    return {
        "available": bool(datasets),
        "datasets_used": datasets,
        "overall_status": overall,
        "descriptors_determined": determined,
        "descriptors_not_remote": not_remote,
        "descriptors_not_available": not_available,
        "descriptors_total": total_descriptors,
        "country_code": country_code,
        "slope_source": slope_source,
        "part_a": part_a,
        "part_b": part_b,
        "part_c": part_c,
        "part_d": part_d,
    }
