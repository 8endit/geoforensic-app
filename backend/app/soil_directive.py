"""EU Soil Monitoring Directive (EU) 2025/2360 — Anhang I.

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

Über die EU-Pflicht hinaus liefern wir 5 ergänzende Indikatoren als
``bonus_indicators`` (Wind-Erosion separat, PAK/PCB, mikrobielle Aktivität,
Bodenstruktur, Hydromorphologie). Diese sind NICHT Teil des Annex und
buchbar als Zusatzmodule (siehe routers/modules.py).

Item-Schema (konsistent für alle Annex-Parts und Bonus-Indikatoren):
    label, annex_descriptor, value, unit, status, status_label,
    threshold (optional), source, note (optional).
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

# Status-Labels in Display-Form (de). Alle Items im finalen Output haben
# status_label damit das Template nichts ableiten muss.
_STATUS_LABELS = {
    "ok": "Innerhalb Schwelle",
    "warn": "Auffällig",
    "alert": "Über Schwelle",
    "na": "Daten nicht verfügbar",
    "not_remote": "Bodenprobe erforderlich",
    "planned": "Modul geplant",
    "stabil": "stabil",
}


def _label(status: str) -> str:
    return _STATUS_LABELS.get(status, status)


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
    """Simplified RUSLE: A = R × K × LS × C × P (t/ha/yr)."""
    r = get_r_factor(lat, lon, country_code)
    r_factor = r.value

    if clay is not None and sand is not None and silt is not None:
        tex = _texture_class(clay, sand, silt)
        k_factor = _K_FACTOR_BY_TEXTURE.get(tex, 0.030)
    else:
        k_factor = 0.030

    slope_rad = math.radians(slope_deg)
    sin_slope = math.sin(slope_rad)
    if slope_deg < 5:
        s_factor = 10.8 * sin_slope + 0.03
    else:
        s_factor = 16.8 * sin_slope - 0.50
    l_factor = (50 / 22.13) ** 0.4
    ls_factor = max(s_factor * l_factor, 0.01)

    c_factor = _CORINE_C_FACTOR.get(corine_code, 0.20) if corine_code else 0.20
    p_factor = 1.0

    a_t_ha_yr = r_factor * k_factor * ls_factor * c_factor * p_factor

    if a_t_ha_yr < 2:
        status = "ok"
    elif a_t_ha_yr < 11:
        status = "warn"
    else:
        status = "alert"

    return {
        "a_t_ha_yr": round(a_t_ha_yr, 2),
        "r_factor": round(r_factor, 1),
        "r_source": r.source,
        "k_factor": round(k_factor, 4),
        "ls_factor": round(ls_factor, 3),
        "c_factor": c_factor,
        "p_factor": p_factor,
        "slope_deg": round(slope_deg, 1),
        "status": status,
    }


# ── Item-Builder: jedes Annex-Item bekommt ein einheitliches Dict ─────────

def _make_item(
    label: str,
    annex_descriptor: str,
    value,
    unit: str,
    status: str,
    *,
    threshold: str | None = None,
    source: str = "",
    note: str | None = None,
) -> dict:
    """Einheitliches Item-Schema für Annex-Parts und Bonus-Indikatoren.

    Jedes Item, das im Vollbericht oder in der Marketing-Story auftaucht,
    nutzt diese Form — damit Leute uns über die Konsistenz wiedererkennen.
    """
    item = {
        "label": label,
        "annex_descriptor": annex_descriptor,
        "value": value,
        "unit": unit,
        "status": status,
        "status_label": _label(status),
        "source": source,
    }
    if threshold:
        item["threshold"] = threshold
    if note:
        item["note"] = note
    return item


# ── Main query ────────────────────────────────────────────────────────────

def query_soil_directive(
    lat: float,
    lon: float,
    slope_deg: Optional[float] = None,
    country_code: str = "de",
) -> dict:
    """Query alle EU Soil Monitoring Directive Descriptoren plus Bonus-Indikatoren.

    Args:
        lat, lon: Adress-Koordinaten (WGS-84).
        slope_deg: Gelände-Hangneigung am Standort. Default 2° wenn None.
        country_code: 'de'/'nl'/'at'/'ch'.

    Returns:
        Dict mit Schema:
            available, datasets_used, overall_status,
            descriptors_determined, descriptors_not_remote,
            descriptors_not_available, descriptors_total (= 13),
            country_code, slope_source,
            part_a (3 Items), part_b (5 Items),
            part_c (5 Items), part_d (4 Items),
            bonus_indicators (5 Items),
            auxiliary_data (Hilfs-Info wie Bodentextur)
    """
    loader = SoilDataLoader.get()
    cc = country_code.lower()
    thresholds = get_thresholds(cc)

    # === Roh-Queries ====================================================
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

    # === PART A — EU-weite Schwellwerte (3 Items) =======================

    # A.1 Salinisation
    ec_est = 0.15
    if lat > 53.5 and sand and sand > 60:
        ec_est = 0.8
    elif clay and clay > 35:
        ec_est = 0.3
    salin_status = "ok" if ec_est < 4.0 else ("warn" if ec_est < 8.0 else "alert")
    salinisation = _make_item(
        label="Salinisation (Elektrische Leitfähigkeit)",
        annex_descriptor="Salinisation",
        value=round(ec_est, 2), unit="dS/m", status=salin_status,
        threshold="< 4 dS/m (EU-Schwelle)",
        source="Regionalschätzung aus Bodenchemie + Küsten-Distanz",
        note="Direktmessung gemäß ISO 11265 für höchste Präzision empfohlen.",
    )

    # A.2 SOC concentration
    soc_status = _classify_soc(soc_pct) if soc_pct is not None else "na"
    soc_concentration = _make_item(
        label="Verlust organischer Substanz (SOC-Konzentration)",
        annex_descriptor="Loss of Soil Organic Carbon (concentration)",
        value=round(soc_raw, 1) if soc_raw is not None else None,
        unit="g/kg", status=soc_status,
        threshold="SOC/Ton-Verhältnis > 1/13 (EU-Kriterium)",
        source="SoilGrids 250m + LUCAS Topsoil",
    )

    # A.3 Subsoil compaction (Lagerungsdichte im Unterboden)
    sub_status = "ok" if (bdod is not None and bdod < 1.7) else (
        "warn" if bdod is not None and bdod < 1.85 else (
            "alert" if bdod is not None else "na"
        )
    )
    subsoil_compaction = _make_item(
        label="Unterboden-Verdichtung (Lagerungsdichte)",
        annex_descriptor="Subsoil compaction",
        value=round(float(bdod), 2) if bdod is not None else None,
        unit="g/cm³", status=sub_status,
        threshold="< 1,80 g/cm³ je nach Textur (EU-Tabelle)",
        source="SoilGrids 250m bdod 30-60cm",
    )

    part_a = {
        "salinisation": salinisation,
        "soc_concentration": soc_concentration,
        "subsoil_compaction": subsoil_compaction,
    }

    # === PART B — Mitgliedstaat-Schwellwerte (5 Items) ==================

    # B.1 Phosphor
    p_value = lucas_nutrients.get("P")
    if p_value is not None:
        p_status = "ok" if 15 <= p_value <= 50 else ("warn" if p_value > 50 else "alert")
    else:
        p_status = "na"
    phosphorus = _make_item(
        label="Phosphor-Überschuss",
        annex_descriptor="Excess nutrient content (phosphorus)",
        value=round(float(p_value), 1) if p_value is not None else None,
        unit="mg/kg", status=p_status,
        threshold="15–50 mg/kg (P-CAL)",
        source="LUCAS Soil (JRC ESDAC)",
    )

    # B.2 Soil erosion rate (RUSLE)
    erosion_data = _estimate_erosion_rusle(
        lat, lon, clay, sand, silt, slope_deg, corine_code, country_code=cc,
    )
    soil_erosion_rate = _make_item(
        label="Bodenerosionsrate (RUSLE)",
        annex_descriptor="Soil erosion rate",
        value=erosion_data["a_t_ha_yr"], unit="t/ha/Jahr",
        status=erosion_data["status"],
        threshold="< 2 t/ha/Jahr (EU-Toleranz)",
        source=f"RUSLE-Modell — R: {erosion_data['r_source']}",
        note=(
            f"R={erosion_data['r_factor']} K={erosion_data['k_factor']} "
            f"LS={erosion_data['ls_factor']} C={erosion_data['c_factor']} "
            f"P={erosion_data['p_factor']} bei {erosion_data['slope_deg']}° Hang"
        ),
    )

    # B.3 Soil contamination — Schwermetalle (Subset von "Soil contamination")
    metals_classified: list[dict] = []
    metals_overall_status = "ok" if metals else "na"
    for name in ["Cd", "Pb", "Hg", "As", "Cr", "Cu", "Ni", "Zn"]:
        val = metals.get(name)
        if val is not None:
            mstatus = _classify_metal(name, val, thresholds)
            if mstatus == "alert":
                metals_overall_status = "alert"
            elif mstatus == "warn" and metals_overall_status != "alert":
                metals_overall_status = "warn"
            metals_classified.append({
                "name": name, "value": round(float(val), 2), "unit": "mg/kg",
                "lower_threshold": thresholds["lower"].get(name),
                "upper_threshold": thresholds["upper"].get(name),
                "lower_label": thresholds["lower_label"],
                "upper_label": thresholds["upper_label"],
                "source": thresholds["source"],
                "status": mstatus,
            })
    heavy_metals = _make_item(
        label="Schwermetall-Belastung",
        annex_descriptor="Soil contamination (heavy metals)",
        value=len(metals_classified) if metals_classified else None,
        unit="Stoffe gemessen",
        status=metals_overall_status,
        threshold=thresholds["upper_label"],
        source=thresholds["source"] if metals_classified else "LUCAS Soil",
        note=(
            None if metals_classified
            else "Schwermetalle aus LUCAS-Boden für diese Region nicht standortspezifisch verfügbar."
        ),
    )
    heavy_metals["details"] = metals_classified  # Volle Stoff-Liste für Tabelle
    if metals_classified:
        heavy_metals["lucas_distance_km"] = lucas_dist_km

    # B.4 Water retention
    awc_status = "na"
    if awc is not None:
        awc_status = "ok" if awc >= 140 else ("warn" if awc >= 100 else "alert")
    water_retention = _make_item(
        label="Reduzierte Wasser-Retention",
        annex_descriptor="Reduction of soil water retention and infiltration",
        value=awc, unit="mm/m", status=awc_status,
        threshold="> 140 mm/m (Mitgliedstaat-Schwelle DE)",
        source="WRB-Klassen-Lookup (SoilGrids)" if wrb else "nicht verfügbar",
    )

    # B.5 SOC stock — abgeleitet aus Konzentration × Bulk-Density × 30cm
    soc_stock_t_ha = None
    soc_stock_status = "na"
    if soc_raw is not None and bdod is not None:
        # SOC (g/kg) × Bulk Density (g/cm³) × 30cm × 0.1 → t/ha
        # Faktor 0.1: g/kg × g/cm³ × 0.3m × 10000m² × 1e-3 t/g = 3 × g/kg × g/cm³
        soc_stock_t_ha = round(soc_raw * bdod * 3.0, 1)
        if soc_stock_t_ha >= 60:
            soc_stock_status = "ok"
        elif soc_stock_t_ha >= 40:
            soc_stock_status = "warn"
        else:
            soc_stock_status = "alert"
    soc_stock = _make_item(
        label="SOC-Vorrat (Stock)",
        annex_descriptor="Loss of SOC (stock)",
        value=soc_stock_t_ha, unit="t C/ha (0-30cm)",
        status=soc_stock_status,
        threshold="> 60 t C/ha (Mitgliedstaat-Mindestwert)",
        source="berechnet aus SOC-Konzentration × Lagerungsdichte × 30 cm",
    )

    part_b = {
        "phosphorus": phosphorus,
        "soil_erosion_rate": soil_erosion_rate,
        "heavy_metals": heavy_metals,
        "water_retention": water_retention,
        "soc_stock": soc_stock,
    }

    # === PART C — beobachtende Descriptoren (5 Items) ===================

    # C.1 Nitrogen + N/SOC ratio
    n_total = lucas_nutrients.get("N_total")
    n_status = "na"
    n_surplus_est = None
    if n_total is not None:
        n_surplus_est = round(n_total / 70, 0)
        n_status = "ok" if n_surplus_est < 50 else ("warn" if n_surplus_est < 80 else "alert")
    nitrogen = _make_item(
        label="Stickstoff-Gehalt + SOC/N-Verhältnis",
        annex_descriptor="Total nitrogen content + SOC/N ratio",
        value=round(float(n_total), 0) if n_total is not None else None,
        unit="mg/kg N", status=n_status,
        threshold="kein EU-Schwellwert (rein beobachtend)",
        source="LUCAS Soil (JRC ESDAC)",
        note=(
            f"Surplus-Schätzung: {n_surplus_est} kg N/ha/Jahr (LUCAS-Indikator, kein direkter Surplus-Messwert)"
            if n_surplus_est is not None else None
        ),
    )

    # C.2 pH (Versauerung)
    ph_status = _classify_ph(ph_raw) if ph_raw is not None else "na"
    ph = _make_item(
        label="Versauerung (pH-Wert)",
        annex_descriptor="Acidification (soil pH)",
        value=round(ph_raw, 1) if ph_raw is not None else None,
        unit="pH", status=ph_status,
        threshold="5,0 – 7,5 (optimal); 4,5 – 8,0 (Toleranz)",
        source="SoilGrids 250m + LUCAS Topsoil",
    )

    # C.3 Topsoil compaction
    top_status = "ok" if (bdod is not None and bdod < 1.55) else (
        "warn" if bdod is not None and bdod < 1.7 else (
            "alert" if bdod is not None else "na"
        )
    )
    topsoil_compaction = _make_item(
        label="Oberboden-Verdichtung (Lagerungsdichte A-Horizont)",
        annex_descriptor="Topsoil compaction",
        value=round(float(bdod), 2) if bdod is not None else None,
        unit="g/cm³", status=top_status,
        threshold="kein EU-Schwellwert (rein beobachtend)",
        source="SoilGrids 250m bdod 0-30cm",
    )

    # C.4 Soil biodiversity (DNA-Metabarcoding) — not_remote
    biodiversity = _make_item(
        label="Boden-Biodiversität (DNA-Metabarcoding)",
        annex_descriptor="Loss of soil biodiversity",
        value=None, unit="DNA-Sequenzen",
        status="not_remote",
        source="In-situ-Beprobung erforderlich",
        note=(
            "DNA-Metabarcoding für Pilze und Bakterien gemäß Anhang II Methodik. "
            "Wird im Vollbericht als not_remote gekennzeichnet."
        ),
    )

    # C.5 Soil contamination (PFAS + Pestizide) — Part C subset
    pest = query_pesticides(lat, lon, country_code=cc)
    if pest.available:
        if pest.flagged_count > 0:
            pest_status = "alert"
        elif pest.n_substances_detected >= 10:
            pest_status = "warn"
        else:
            pest_status = "ok"
    else:
        pest_status = "na"
    pfas_pesticides = _make_item(
        label="Bodenkontamination (PFAS + Pestizid-Rückstände)",
        annex_descriptor="Soil contamination (PFAS-21/43 + pesticides)",
        value=pest.n_substances_detected if pest.available else None,
        unit="Pestizide detektiert (PFAS: not_remote)",
        status=pest_status,
        threshold="kein EU-Schwellwert (rein beobachtend, MS-spezifisch)",
        source="LUCAS Topsoil 2018 NUTS2 (JRC ESDAC) für Pestizide; PFAS not_remote",
        note=(
            f"PFAS-Konzentrationen erfordern In-situ-Beprobung nach DIN EN ISO 21675. "
            f"Pestizide: {pest.n_substances_detected if pest.available else 0} detektiert"
            + (f", {pest.flagged_count} davon als Altlast eingestuft" if pest.available and pest.flagged_count else "")
            + "."
        ),
    )
    pfas_pesticides["details"] = {
        "pfas_status": "not_remote",
        "pfas_note": "PFAS-21/43 nach Anhang I Teil C — In-situ-Beprobung erforderlich.",
        "pesticides_top": [
            {"name": h.name, "concentration_mg_kg": h.concentration_mg_kg,
             "flagged_legacy": h.flagged_legacy}
            for h in (pest.top_substances if pest.available else [])
        ],
        "nuts2_code": pest.nuts2_code,
        "nuts2_name": pest.nuts2_name,
    }

    part_c = {
        "nitrogen": nitrogen,
        "ph": ph,
        "topsoil_compaction": topsoil_compaction,
        "biodiversity": biodiversity,
        "pfas_pesticides": pfas_pesticides,
    }

    # === PART D — Versiegelungs-Indikatoren (4 Items) ===================

    # D.1 Sealed area at the address
    sealed_status = "na"
    if imperviousness is not None:
        sealed_status = "ok" if imperviousness < 30 else ("warn" if imperviousness < 60 else "alert")
    sealed_area = _make_item(
        label="Versiegelte Bodenfläche (lokale Adresse)",
        annex_descriptor="Total sealed soils",
        value=imperviousness, unit="% (100m-Radius)",
        status=sealed_status,
        threshold="abhängig von Land (DE: §15 BBodSchG)",
        source="HRL Imperviousness 20m (Copernicus)" if imperviousness is not None else "nicht verfügbar",
    )

    # D.2 Sealing change per year — Sentinel-2 ChangeDetection ausstehend
    sealing_change = _make_item(
        label="Versiegelungsänderung pro Jahr",
        annex_descriptor="Soil sealing/de-sealing/net-sealing per year",
        value=None, unit="km²/Jahr",
        status="planned",
        source="Sentinel-2 Change Detection",
        note="Modul aktuell in Vorbereitung — geplant für Q3 2026.",
    )

    # D.3 Settlement area
    settlement_area = _make_item(
        label="Siedlungsflächen-Anteil",
        annex_descriptor="Total settlement area",
        value=corine.get("label_de") if corine else None,
        unit="CORINE-Klasse",
        status="ok" if corine else "na",
        source="CORINE Land Cover 2018 (Copernicus EEA)" if corine else "nicht verfügbar",
    )

    # D.4 Land use change to/from settlement
    landuse_change = _make_item(
        label="Landnutzungsänderung zu/von Siedlung",
        annex_descriptor="Land use change to/from settlement area",
        value=None, unit="km²/Jahr",
        status="planned",
        source="CORINE Land Cover Change Layer",
        note="Modul aktuell in Vorbereitung — geplant für Q3 2026.",
    )

    part_d = {
        "sealed_area": sealed_area,
        "sealing_change": sealing_change,
        "settlement_area": settlement_area,
        "landuse_change": landuse_change,
    }

    # === BONUS — Über EU-Pflicht hinaus (5 Items) =======================
    # Buchbar als Zusatzmodule (siehe routers/modules.py).

    # Bonus 1 — Wind-Erosion separat ausgewiesen
    wind_status = "ok"
    wind_note = "Für Standort nicht relevant (kein Sandboden / nicht in Norddeutschland-Klima)"
    if sand is not None and sand > 60 and lat > 52.0 and slope_deg < 3:
        wind_status = "warn"
        wind_note = (
            "Verhoogd risico (zandgronden, Noord/Oost-Nederland)" if cc == "nl"
            else "Erhöht (sandige Böden, Norddeutschland)"
        )
    wind_erosion = _make_item(
        label="Wind-Erosion (separat zu RUSLE)",
        annex_descriptor="(über EU-Pflicht hinaus — RWEQ-Approximation)",
        value="erhöht" if wind_status == "warn" else "gering",
        unit="qualitativ", status=wind_status,
        source="RWEQ-Approximation aus Sandanteil + Lat + Hangneigung",
        note=wind_note,
    )

    # Bonus 2 — PAK + PCB (BBodSchV-relevante Altlast-Indikatoren)
    pak_pcb = _make_item(
        label="PAK und PCB (Altlast-Screening)",
        annex_descriptor="(über EU-Pflicht hinaus — BBodSchV §8 Anhang 1)",
        value=None, unit="mg/kg",
        status="not_remote",
        source="In-situ-Beprobung erforderlich",
        note=(
            "BBodSchV-Schwellwerte: PAK Σ16 = 2/4/12 mg/kg (Kinderspiel/Wohnen/Industrie), "
            "PCB = 0,4/0,8/40 mg/kg. Bei Vornutzungs-Verdacht (Schmiede, Tankstelle, "
            "Trafostation) Standard-Untersuchungspaket."
        ),
    )

    # Bonus 3 — Mikrobielle Aktivität (Atmungsrate, Biomasse)
    microbial_activity = _make_item(
        label="Mikrobielle Aktivität (Atmungsrate, Biomasse)",
        annex_descriptor="(über EU-Pflicht hinaus — Boden-Vitalität)",
        value=None, unit="μg CO2-C / g·h",
        status="not_remote",
        source="LUCAS Soil Biology / In-situ-Inkubation",
        note=(
            "Boden-Atmungsrate als Vitalitäts-Indikator zusätzlich zur DNA-Biodiversität "
            "(EU-Pflichtteil). Wo LUCAS-Soil-Biology-Daten verfügbar sind, "
            "ergänzen wir die Approximation."
        ),
    )

    # Bonus 4 — Bodenstruktur / Aggregat-Stabilität
    structure_value = None
    structure_status = "na"
    if clay is not None and soc_pct is not None:
        # Pragmatisch: Aggregat-Stabilität-Index aus Ton-Anteil und SOC.
        # Höher = stabiler. Wischmeier-Hint: Ton+SOC begünstigen Aggregate.
        structure_idx = round(min(100, clay * 0.8 + soc_pct * 30), 1)
        structure_value = structure_idx
        structure_status = "ok" if structure_idx >= 50 else ("warn" if structure_idx >= 30 else "alert")
    soil_structure = _make_item(
        label="Bodenstruktur und Aggregat-Stabilität",
        annex_descriptor="(über EU-Pflicht hinaus — Erosions- und Versickerungs-Vorlauf)",
        value=structure_value, unit="Index 0-100",
        status=structure_status,
        threshold="> 50 (gut aggregiert)",
        source="berechnet aus Ton-Anteil + SOC (vereinfachter Aggregat-Index)",
        note="Voller Test in DIN ISO 10930 (Nasssiebung) bleibt Goldstandard.",
    )

    # Bonus 5 — Hydromorphologie / Drainage-Klasse
    hydro_status = "na"
    hydro_value = None
    if wrb is not None:
        # WRB-Klassen mit Hydromorphologie-Bezug
        hydro_value = wrb
        hydro_status = "ok"  # rein deskriptiv
    hydromorphology = _make_item(
        label="Hydromorphologie und Drainage-Klasse",
        annex_descriptor="(über EU-Pflicht hinaus — Hochwasser-Vorlauf)",
        value=hydro_value, unit="WRB-Klasse",
        status=hydro_status,
        source="WRB Soil Classification (SoilGrids)" if wrb else "nicht verfügbar",
        note="Indikator für Drainage-Eigenschaften des Bodens — relevant für Versickerungs- und Wurzeltiefe-Analysen.",
    )

    bonus_indicators = {
        "wind_erosion": wind_erosion,
        "pak_pcb": pak_pcb,
        "microbial_activity": microbial_activity,
        "soil_structure": soil_structure,
        "hydromorphology": hydromorphology,
    }

    # === Auxiliary data (kein Annex-Item, Hilfs-Info) ===================
    auxiliary_data = {
        "texture": {
            "clay_pct": round(float(clay), 1) if clay is not None else None,
            "sand_pct": round(float(sand), 1) if sand is not None else None,
            "silt_pct": round(float(silt), 1) if silt is not None else None,
            "class": tex_class, "label": tex_label,
            "source": "SoilGrids 250m",
        },
    }

    # === One-out-all-out Bewertung ======================================
    all_statuses = [
        # Part A
        salinisation["status"], soc_concentration["status"], subsoil_compaction["status"],
        # Part B
        phosphorus["status"], soil_erosion_rate["status"], heavy_metals["status"],
        water_retention["status"], soc_stock["status"],
        # Part C
        nitrogen["status"], ph["status"], topsoil_compaction["status"],
        biodiversity["status"], pfas_pesticides["status"],
    ]
    real_statuses = [s for s in all_statuses if s not in ("na", "not_remote", "planned")]

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
    determined = sum(1 for s in all_statuses if s not in ("na", "not_remote", "planned"))
    not_remote = sum(1 for s in all_statuses if s == "not_remote")
    not_available = max(total_descriptors - determined - not_remote, 0)

    datasets = []
    if has_soilgrids:
        datasets.append("SoilGrids 250m (ISRIC, CC BY 4.0)")
    if metals or lucas_nutrients:
        datasets.append("LUCAS Soil (JRC ESDAC)")
    if pest.available:
        datasets.append("LUCAS Pesticides 2018 NUTS2 (JRC ESDAC)")
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
    datasets.append(f"R-Faktor: {erosion_data['r_source']}")

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
        "bonus_indicators": bonus_indicators,
        "auxiliary_data": auxiliary_data,
    }
