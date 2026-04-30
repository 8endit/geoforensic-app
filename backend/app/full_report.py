"""Full Bodenbericht PDF — all data sources combined.

Sections:
1. Header + Address + Ampel Badge
2. Bodenbewegung (EGMS InSAR)
3. Schwermetalle (LUCAS Topsoil) + BBodSchV Vergleich
4. Bodenqualitaet (SoilGrids: pH, SOC, Textur, Dichte)
5. Naehrstoffe (LUCAS: P, N)
6. Personalisierte Einschaetzung (Quiz-Antworten)
7. Datenquellen + Disclaimer
"""

import io
import os
import tempfile
from datetime import datetime, timezone

from fpdf import FPDF

from app.report_charts import geoscore_gauge, metals_chart, soil_quality_bars, soil_texture_pie
from app.soil_data import BBODSCHV_VORSORGE, SOILGRIDS_PROPERTIES

# ── Font discovery ──────────────────────────────────────────────────
_FONT_PATHS = [
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
_FONT_BOLD_PATHS = [
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _find_font(paths: list[str]) -> str | None:
    for p in paths:
        if os.path.isfile(p):
            return p
    return None


# ── Ampel helpers ───────────────────────────────────────────────────

def _ampel_color(a: str) -> tuple[int, int, int]:
    return {"gruen": (91, 154, 111), "gelb": (196, 169, 77), "rot": (184, 84, 80)}.get(a, (150, 150, 150))


def _status_color(s: str) -> tuple[int, int, int]:
    return {"ok": (91, 154, 111), "warn": (196, 169, 77), "critical": (184, 84, 80)}.get(s, (150, 150, 150))


# ── Quiz-text mappings ──────────────────────────────────────────────

_NUTZUNG = {
    "Eigenheim / Garten": "Als Eigenheimbesitzer ist die Stabilitaet Ihres Bodens besonders wichtig fuer den Werterhalt Ihrer Immobilie und die Sicherheit Ihrer Familie.",
    "Landwirtschaft": "Fuer landwirtschaftliche Nutzung ist Bodenqualitaet und -stabilitaet entscheidend fuer Ertragssicherheit.",
    "Ich plane einen Hauskauf": "Vor einem Grundstueckskauf ist ein Bodenscreening besonders wichtig: Versteckte Bodenprobleme koennen zu erheblichen Kosten fuehren.",
    "Gewerblich": "Bei gewerblicher Nutzung sind Bodenstabilitaet und Altlasten relevant fuer Genehmigungen und Versicherungen.",
}

_DRINGLICHKEIT = {
    "Sofort – es eilt": "Handlungsempfehlung: Bei erhoehten Werten empfehlen wir eine zeitnahe Begutachtung durch einen Sachverstaendigen.",
    "Innerhalb der naechsten 2 Wochen": "Handlungsempfehlung: Planen Sie bei auffaelligen Werten eine weiterfuehrende Untersuchung ein.",
    "Ich informiere mich nur": "Handlungsempfehlung: Beobachten Sie die Entwicklung. Erneute Pruefung in 6-12 Monaten empfohlen.",
}


def generate_full_report(
    address: str,
    lat: float,
    lon: float,
    # EGMS data
    ampel: str,
    point_count: int,
    mean_velocity: float,
    max_velocity: float,
    geo_score: int | None,
    # Soil data
    soil_profile: dict,
    # Quiz answers
    answers: dict | None = None,
    # NRW Bergbau (None for non-NRW addresses; populated dict for NRW)
    mining_data: dict | None = None,
    # DWD KOSTRA Starkregen (None if loader not initialized; dict otherwise)
    kostra_data: dict | None = None,
    # BfG Hochwasser-Szenarien HQ_haeufig / HQ100 / HQ_extrem
    flood_data: dict | None = None,
    # EU Soil Monitoring Directive 2025/2360 — 16 descriptors with provenance
    soil_directive_data: dict | None = None,
    # Altlasten (NL: PDOK Bodemloket; DE: CORINE land-use proxy + auth-enquiry hint)
    altlasten_data: dict | None = None,
    # Slope / Geländeprofil from multi-scale Open-Elevation / OpenTopoData lookup
    slope_data: dict | None = None,
    # ISO 3166-1 alpha-2 country code from geocoding ("de"/"nl"/"at"/"ch")
    country_code: str = "de",
) -> bytes:
    """Generate a comprehensive Bodenbericht PDF."""
    answers = answers or {}
    now = datetime.now(timezone.utc)
    has_egms = point_count > 0
    soilgrids = soil_profile.get("soilgrids", {})
    metals = soil_profile.get("metals", {})
    metal_status = soil_profile.get("metal_status", {})
    nutrients = soil_profile.get("nutrients", {})
    lucas_dist = soil_profile.get("lucas_distance_km", -1)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Register font
    fr = _find_font(_FONT_PATHS)
    fb = _find_font(_FONT_BOLD_PATHS)
    if fr:
        pdf.add_font("R", "", fr)
        pdf.add_font("R", "B", fb or fr)
        pdf.add_font("R", "I", fr)
        fn = "R"
    else:
        fn = "Helvetica"

    # ════════════════════════════════════════════════════════════════
    # PAGE 1: Overview + EGMS
    # ════════════════════════════════════════════════════════════════
    pdf.add_page()

    # Header
    pdf.set_fill_color(15, 32, 64)
    pdf.rect(0, 0, 210, 38, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(fn, "B", 26)
    pdf.set_y(10)
    pdf.cell(0, 10, "BODENBERICHT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fn, "", 10)
    pdf.set_text_color(180, 200, 220)
    pdf.cell(0, 6, "Umfassende Standortanalyse", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(34, 197, 94)
    pdf.set_line_width(1.5)
    pdf.line(10, 40, 200, 40)
    pdf.set_y(45)

    # Address
    pdf.set_text_color(30, 30, 30)
    pdf.set_font(fn, "B", 13)
    pdf.multi_cell(0, 7, address)
    pdf.set_font(fn, "", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 5, f"{lat:.5f}, {lon:.5f}  |  {now.strftime('%d.%m.%Y %H:%M')} UTC", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.ln(6)

    # ── Section: Bodenbewegung ──────────────────────────────────────
    _section_header(pdf, fn, "1. Bodenbewegung (InSAR-Satellitendaten)")

    # Ampel
    r, g, b = _ampel_color(ampel)
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(fn, "B", 14)
    label = {"gruen": "UNAUFF\u00c4LLIG", "gelb": "AUFF\u00c4LLIG", "rot": "KRITISCH"}.get(ampel, "KEINE DATEN") if has_egms else "KEINE DATEN"
    pdf.cell(70, 12, f"  {label}", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # KPIs + GeoScore gauge side by side
    pdf.set_text_color(30, 30, 30)
    _kpi_row(pdf, fn, [
        (str(point_count), "Messpunkte"),
        (f"{mean_velocity:.1f} mm/a" if has_egms else "-", "Mittl. Geschw."),
        (f"{max_velocity:.1f} mm/a" if has_egms else "-", "Max. Geschw."),
    ])

    # GeoScore gauge chart
    gauge_png = geoscore_gauge(geo_score, ampel)
    if gauge_png:
        gauge_path = _tmp_png(gauge_png)
        pdf.image(gauge_path, x=130, y=pdf.get_y() - 26, w=65)
        os.unlink(gauge_path)
    pdf.ln(3)

    pdf.set_font(fn, "", 9)
    pdf.set_text_color(80, 80, 80)
    if has_egms:
        if ampel == "gruen":
            pdf.multi_cell(0, 4, "Keine auffaelligen Bodenbewegungen im Untersuchungsradius. Stabile Lage.")
        elif ampel == "gelb":
            pdf.multi_cell(0, 4, "Vereinzelt erhoehte Bodenbewegungen gemessen. Weitere Beobachtung empfohlen.")
        else:
            pdf.multi_cell(0, 4, "Kritische Bodenbewegungen gemessen. Fachliche Einschaetzung dringend empfohlen.")
    else:
        pdf.multi_cell(0, 4, "Fuer diesen Standort liegen keine InSAR-Satellitendaten vor.")
    pdf.ln(4)

    # ── Section: Schwermetalle ──────────────────────────────────────
    _section_header(pdf, fn, "2. Schwermetall-Analyse")

    if metals:
        pdf.set_font(fn, "", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 4, f"Basierend auf LUCAS Topsoil-Daten (naechster Messpunkt: {lucas_dist} km)", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        # Table header
        pdf.set_font(fn, "B", 8)
        pdf.set_fill_color(240, 240, 240)
        pdf.set_text_color(50, 50, 50)
        w = [30, 30, 35, 35, 30]
        pdf.cell(w[0], 6, "Stoff", border=1, fill=True)
        pdf.cell(w[1], 6, "Messwert", border=1, fill=True, align="R")
        pdf.cell(w[2], 6, "Einheit", border=1, fill=True, align="C")
        pdf.cell(w[3], 6, "Vorsorgewert", border=1, fill=True, align="R")
        pdf.cell(w[4], 6, "Status", border=1, fill=True, align="C")
        pdf.ln()

        pdf.set_font(fn, "", 8)
        for metal in ["Cd", "Pb", "Hg", "As", "Cr", "Cu", "Ni", "Zn"]:
            ms = metal_status.get(metal, {})
            val = ms.get("value", metals.get(metal))
            threshold = ms.get("threshold", BBODSCHV_VORSORGE.get(metal, ""))
            status = ms.get("status", "")

            if status:
                sr, sg, sb = _status_color(status)
                status_text = {"ok": "OK", "warn": "Erhoht", "critical": "Kritisch"}.get(status, "")
            else:
                sr, sg, sb = 150, 150, 150
                status_text = "-"

            pdf.set_text_color(50, 50, 50)
            pdf.cell(w[0], 5, metal, border=1)
            pdf.cell(w[1], 5, f"{val:.2f}" if val else "-", border=1, align="R")
            pdf.cell(w[2], 5, "mg/kg", border=1, align="C")
            pdf.cell(w[3], 5, f"{threshold}" if threshold else "-", border=1, align="R")
            pdf.set_text_color(sr, sg, sb)
            pdf.set_font(fn, "B", 8)
            pdf.cell(w[4], 5, status_text, border=1, align="C")
            pdf.set_font(fn, "", 8)
            pdf.ln()
        pdf.ln(2)

        pdf.set_text_color(100, 100, 100)
        pdf.set_font(fn, "", 7)
        pdf.cell(0, 4, "Vergleichswerte: BBodSchV Vorsorgewerte (Bundesbodenschutzverordnung)", new_x="LMARGIN", new_y="NEXT")

        # Metals bar chart
        chart_png = metals_chart(metals, BBODSCHV_VORSORGE)
        if chart_png:
            chart_path = _tmp_png(chart_png)
            pdf.ln(2)
            pdf.image(chart_path, x=10, w=140)
            os.unlink(chart_path)
    else:
        pdf.set_font(fn, "", 9)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 6, "Keine Schwermetall-Daten fuer diesen Standort verfuegbar.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ════════════════════════════════════════════════════════════════
    # PAGE 2: Bergbau + Soil quality + Nutrients + Personalization
    # ════════════════════════════════════════════════════════════════
    pdf.add_page()

    # ── Section: Bergbau / Altbergbau ───────────────────────────────
    _section_bergbau(pdf, fn, mining_data)

    # ── Section: Hochwasser (BfG HWRM) ──────────────────────────────
    _section_flood(pdf, fn, flood_data)

    # ── Section: Niederschlag / Starkregen (KOSTRA) ─────────────────
    _section_kostra(pdf, fn, kostra_data)

    # ── Section: Bodenqualitaet ─────────────────────────────────────
    _section_header(pdf, fn, "6. Bodenqualitaet (SoilGrids 250m)")

    if any(v is not None for v in soilgrids.values()):
        pdf.set_font(fn, "B", 8)
        pdf.set_fill_color(240, 240, 240)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(60, 6, "Eigenschaft", border=1, fill=True)
        pdf.cell(30, 6, "Wert", border=1, fill=True, align="R")
        pdf.cell(30, 6, "Einheit", border=1, fill=True, align="C")
        pdf.cell(40, 6, "Bewertung", border=1, fill=True, align="C")
        pdf.ln()

        pdf.set_font(fn, "", 8)
        for prop, meta in SOILGRIDS_PROPERTIES.items():
            val = soilgrids.get(prop)
            if val is None:
                continue
            assessment = _assess_soilgrid(prop, val)
            ar, ag, ab = _status_color(assessment)

            pdf.set_text_color(50, 50, 50)
            pdf.cell(60, 5, meta["label"], border=1)
            pdf.cell(30, 5, f"{val:.1f}" if isinstance(val, float) else str(val), border=1, align="R")
            pdf.cell(30, 5, meta["unit"], border=1, align="C")
            pdf.set_text_color(ar, ag, ab)
            pdf.set_font(fn, "B", 8)
            label = {"ok": "Normal", "warn": "Auffaellig", "critical": "Kritisch"}.get(assessment, "-")
            pdf.cell(40, 5, label, border=1, align="C")
            pdf.set_font(fn, "", 8)
            pdf.ln()
        pdf.ln(2)

        # Visual: quality indicator bars
        quality_png = soil_quality_bars(soilgrids)
        if quality_png:
            qpath = _tmp_png(quality_png)
            pdf.ln(2)
            pdf.image(qpath, x=10, w=140)
            os.unlink(qpath)
            pdf.ln(2)

        # Texture pie chart + text
        clay = soilgrids.get("clay")
        sand = soilgrids.get("sand")
        silt = soilgrids.get("silt")
        if clay is not None and sand is not None and silt is not None:
            texture = _classify_texture(clay, sand, silt)
            pie_png = soil_texture_pie(clay, sand, silt)
            if pie_png:
                pie_path = _tmp_png(pie_png)
                pdf.image(pie_path, x=10, w=50)
                os.unlink(pie_path)
            pdf.set_text_color(50, 50, 50)
            pdf.set_font(fn, "B", 9)
            pdf.cell(0, 5, f"Bodenart: {texture}", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font(fn, "", 9)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 6, "Keine SoilGrids-Daten fuer diesen Standort.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── Section: Naehrstoffe ────────────────────────────────────────
    _section_header(pdf, fn, "7. Naehrstoffe")

    if nutrients:
        pdf.set_font(fn, "", 9)
        pdf.set_text_color(50, 50, 50)
        p_val = nutrients.get("P")
        n_val = nutrients.get("N_total")
        if p_val is not None:
            pdf.cell(0, 5, f"Phosphor (P): {p_val:.1f} mg/kg  {'(optimal)' if 30 <= p_val <= 80 else '(auffaellig)' if p_val > 80 else '(niedrig)'}", new_x="LMARGIN", new_y="NEXT")
        if n_val is not None:
            pdf.cell(0, 5, f"Gesamtstickstoff (N): {n_val:.0f} mg/kg", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(fn, "", 7)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 4, f"Quelle: LUCAS Topsoil Survey (naechster Messpunkt: {lucas_dist} km)", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font(fn, "", 9)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 6, "Keine Naehrstoffdaten verfuegbar.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # ── Section: Gelaendeprofil (Slope, Aspect) ─────────────────────
    if slope_data and slope_data.get("available"):
        _render_slope(pdf, fn, slope_data)

    # ── Section: EU-Bodenueberwachungsrichtlinie (16 Descriptoren) ──
    if soil_directive_data and soil_directive_data.get("available"):
        _render_soil_directive(pdf, fn, soil_directive_data)

    # ── Section: Pestizid-Rueckstaende (LUCAS NUTS2) ────────────────
    if soil_directive_data:
        oc = soil_directive_data.get("part_b", {}).get("organic_contaminants") or {}
        if oc.get("pesticides"):
            _render_pesticides(pdf, fn, oc["pesticides"])

    # ── Section: Altlasten / Bodenkontaminations-Indikator ──────────
    if altlasten_data and altlasten_data.get("available"):
        _render_altlasten(pdf, fn, altlasten_data)

    # ── Section: Individuelle Einschaetzung ─────────────────────────
    if answers:
        _section_header(pdf, fn, "12. Ihre individuelle Einschaetzung")
        pdf.set_font(fn, "", 9)
        pdf.set_text_color(50, 50, 50)

        nutzung = answers.get("nutzung", "")
        if nutzung in _NUTZUNG:
            pdf.multi_cell(0, 5, _NUTZUNG[nutzung])
            pdf.ln(2)

        dringlichkeit = answers.get("dringlichkeit", "")
        if dringlichkeit in _DRINGLICHKEIT:
            pdf.set_font(fn, "B", 9)
            pdf.multi_cell(0, 5, _DRINGLICHKEIT[dringlichkeit])
        pdf.ln(4)

    # ── Datenquellen ────────────────────────────────────────────────
    _section_header(pdf, fn, "Gepruefte Datenquellen")
    pdf.set_font(fn, "", 8)
    has_mining = bool(mining_data and not mining_data.get("error"))
    has_kostra = bool(kostra_data and kostra_data.get("available"))
    has_flood = bool(flood_data and not flood_data.get("error"))
    has_directive = bool(soil_directive_data and soil_directive_data.get("available"))
    has_pesticides = bool(
        soil_directive_data
        and (soil_directive_data.get("part_b", {})
             .get("organic_contaminants", {})
             .get("pesticides", {}).get("n_detected", 0)) > 0
    )
    has_corine = bool(
        soil_directive_data
        and soil_directive_data.get("part_d", {}).get("corine") is not None
    )
    has_imperv = bool(
        soil_directive_data
        and soil_directive_data.get("part_d", {}).get("imperviousness_pct") is not None
    )
    has_altlasten_real = bool(
        altlasten_data and altlasten_data.get("data_kind") == "behoerden-kataster"
    )
    has_altlasten_proxy = bool(
        altlasten_data and altlasten_data.get("data_kind") == "land-use-indikator"
    )
    has_slope = bool(slope_data and slope_data.get("available"))
    slope_src_label = (slope_data or {}).get("source", "")
    is_nl = country_code.lower() == "nl"
    threshold_label = (
        "NL Circulaire bodemsanering 2013, Bijlage 1" if is_nl
        else "DE BBodSchV §8 Anhang 2 (Vorsorge/Massnahme)"
    )
    sources = [
        (has_egms, "Copernicus EGMS L3 Ortho (Sentinel-1, 2019-2022)"),
        (True, "Nominatim / OpenStreetMap (Geocodierung)"),
        (bool(metals), "LUCAS Topsoil Survey (Schwermetalle, Naehrstoffe, JRC ESDAC)"),
        (bool(metals), f"Schwermetall-Schwellen: {threshold_label}"),
        (bool(soilgrids.get("phh2o")), "SoilGrids 250m (pH, SOC, Textur, Dichte, ISRIC CC BY 4.0)"),
        (has_directive, "EU-Bodenueberwachungsrichtlinie 2025/2360 (16 Descriptoren)"),
        (has_pesticides, "LUCAS Topsoil 2018 Pestizid-Rueckstaende (NUTS2-aggregiert, JRC ESDAC)"),
        (has_corine, "CORINE Land Cover 2018 v2020_20u1 (Copernicus EEA)"),
        (has_imperv, "HRL Imperviousness 20m (Copernicus Land Monitoring Service)"),
        (has_mining, "Bergbauberechtigungen NRW (Bezirksregierung Arnsberg, dl-de/by-2.0)"),
        (has_flood, "BfG Hochwassergefahrenkarten HWRM-RL (DL-DE/Zero-2.0)"),
        (has_kostra, "DWD KOSTRA-DWD-2020 Starkregen (GeoNutzV)"),
        (False, "Radon-Vorsorgegebiete (Landesabhaengig, in Vorbereitung)"),
        (False, "Erdbebenzonen DIN EN 1998-1/NA (in Vorbereitung)"),
        (has_altlasten_real, "PDOK Bodemloket WBB-Lokationen (CC-BY 4.0)"),
        (has_altlasten_proxy, "Altlasten-Indikator via CORINE Land Cover (Proxy, kein Kataster)"),
        (has_slope, f"Gelaendemodell: {slope_src_label}" if has_slope else "Gelaendemodell (Slope/Aspect)"),
    ]
    for active, name in sources:
        pdf.set_text_color(34, 197, 94) if active else pdf.set_text_color(180, 180, 180)
        pdf.set_font(fn, "B", 9)
        pdf.cell(8, 5, "+" if active else "-")
        pdf.set_text_color(60, 60, 60) if active else pdf.set_text_color(150, 150, 150)
        pdf.set_font(fn, "", 8)
        pdf.cell(0, 5, name, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── Disclaimer ──────────────────────────────────────────────────
    pdf.set_draw_color(220, 220, 220)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_font(fn, "I", 7)
    pdf.set_text_color(130, 130, 130)
    pdf.multi_cell(0, 3.5, (
        "Hinweis: Dieser Bodenbericht ist ein automatisiertes Datenscreening auf Basis "
        "oeffentlich verfuegbarer Fernerkundungs- und Bodendaten. Er ersetzt keine "
        "Ortsbesichtigung, Laboranalyse oder fachliche Einzelfallbewertung durch einen "
        "zugelassenen Sachverstaendigen gem. BBodSchG. Messwerte basieren auf regionalen "
        "Durchschnittswerten (LUCAS, SoilGrids) und nicht auf standortspezifischen Beprobungen. "
        "Generated using European Union's Copernicus Land Monitoring Service information."
    ))
    pdf.ln(2)
    pdf.set_font(fn, "", 7)
    pdf.set_text_color(170, 170, 170)
    pdf.cell(0, 4, f"(c) Bodenbericht {now.year} | bodenbericht.de", new_x="LMARGIN", new_y="NEXT")

    return pdf.output()


# ── Helpers ─────────────────────────────────────────────────────────

def _tmp_png(data: bytes) -> str:
    """Write PNG bytes to a temp file and return the path."""
    f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    f.write(data)
    f.close()
    return f.name


def _section_bergbau(pdf: FPDF, fn: str, mining_data: dict | None) -> None:
    """Render the "Bergbau / Altbergbau" section.

    Three states:
    - ``mining_data is None``    → out-of-scope notice (non-NRW address)
    - ``mining_data["error"]``   → service-unavailable notice
    - ``in_zone False``          → all-clear for the 200 m search bbox
    - ``in_zone True``           → list of overlapping mining-rights fields
    """
    _section_header(pdf, fn, "3. Bergbau / Altbergbau")
    pdf.set_font(fn, "", 9)
    pdf.set_text_color(80, 80, 80)

    if mining_data is None:
        pdf.multi_cell(0, 5, (
            "Die Auswertung von Bergbauberechtigungen ist aktuell nur fuer "
            "Adressen in Nordrhein-Westfalen integriert (Quelle: "
            "Bezirksregierung Arnsberg). Fuer Standorte ausserhalb NRW "
            "wenden Sie sich bitte an das jeweilige Landes-Bergamt."
        ))
        pdf.ln(4)
        return

    if mining_data.get("error"):
        pdf.multi_cell(0, 5, (
            "Die Bergbau-Datenquelle (Bezirksregierung Arnsberg) war zum "
            "Zeitpunkt der Berichterstellung nicht erreichbar. Bitte "
            "fordern Sie ggf. einen aktualisierten Bericht an oder "
            "konsultieren Sie das offizielle WMS direkt."
        ))
        pdf.ln(4)
        return

    fields = mining_data.get("fields") or []
    if not mining_data.get("in_zone") or not fields:
        pdf.set_text_color(91, 154, 111)  # green
        pdf.set_font(fn, "B", 9)
        pdf.cell(0, 6, "Kein Bergbau-Verdachtsgebiet im Untersuchungsumfeld",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(80, 80, 80)
        pdf.set_font(fn, "", 8)
        pdf.multi_cell(0, 4, (
            "Im 200-Meter-Umkreis dieser Adresse sind keine eingetragenen "
            "Bergbauberechtigungen (gueltig oder erloschen) bekannt."
        ))
        pdf.ln(4)
        return

    # in_zone, with one or more overlapping fields
    pdf.set_text_color(196, 169, 77)  # yellow
    pdf.set_font(fn, "B", 9)
    pdf.cell(0, 6, f"Bergbauberechtigung im Umfeld: {len(fields)} Eintrag/Eintraege",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(50, 50, 50)
    pdf.set_font(fn, "", 8)

    for f in fields:
        name = f.get("name") or "(ohne Bezeichnung)"
        mineral = f.get("mineral") or "n.a."
        kind = f.get("type") or "n.a."
        valid_from = f.get("valid_from") or ""
        valid_to = f.get("valid_to") or ""
        period = " – ".join(p for p in (valid_from, valid_to) if p) or "Zeitraum unbekannt"

        pdf.set_font(fn, "B", 8)
        pdf.multi_cell(0, 4.5, name)
        pdf.set_font(fn, "", 8)
        pdf.cell(0, 4.5, f"  Rohstoff: {mineral}    Art: {kind}    Zeitraum: {period}",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.5)

    pdf.ln(2)
    pdf.set_font(fn, "I", 7)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 3.5, (
        "Eine Bergbauberechtigung in der Naehe der Adresse bedeutet nicht "
        "automatisch eine konkrete Gefaehrdung. Sie ist ein Hinweis darauf, "
        "dass im Untergrund Abbau stattgefunden hat oder vorgesehen war "
        "und ist im Einzelfall durch ein qualifiziertes Bergbau-Fachgutachten "
        "zu bewerten."
    ))
    pdf.ln(2)


def _section_flood(pdf: FPDF, fn: str, flood_data: dict | None) -> None:
    """Render the "Hochwasser" section using the BfG HWRM-RL aggregate WMS.

    Three states:
    - ``flood_data is None``                       → "wird in Folgeversion ergaenzt"
    - top-level ``error`` set                      → service-unavailable notice
    - all three scenarios ``in_zone is False``     → all-clear (green)
    - any scenario ``in_zone is True``             → scenario list with risk badge
    """
    _section_header(pdf, fn, "4. Hochwasser (BfG HWRM-RL)")
    pdf.set_font(fn, "", 9)
    pdf.set_text_color(80, 80, 80)

    if flood_data is None:
        pdf.multi_cell(0, 5, (
            "Die bundesweite Hochwasser-Auswertung (BfG, HWRM-Richtlinie) "
            "wird in einer Folgeversion dieses Berichts ergaenzt."
        ))
        pdf.ln(4)
        return

    if flood_data.get("error"):
        pdf.multi_cell(0, 5, (
            "Die BfG-Hochwasserdaten waren zum Zeitpunkt der Berichterstellung "
            "nicht erreichbar. Bitte fordern Sie ggf. einen aktualisierten "
            "Bericht an oder konsultieren Sie das BfG-Geoportal "
            "(geoportal.bafg.de) direkt."
        ))
        pdf.ln(4)
        return

    scenarios = flood_data.get("scenarios") or {}
    haeufig = scenarios.get("haeufig", {})
    hq100 = scenarios.get("hq100", {})
    extrem = scenarios.get("extrem", {})

    # Risk-class derivation: häufig > HQ100 > extrem (descending severity).
    if haeufig.get("in_zone"):
        risk_label = "BETROFFEN — haeufiges Hochwasser"
        risk_color = (184, 84, 80)  # red
    elif hq100.get("in_zone"):
        risk_label = "BETROFFEN — 100-jaehriges Hochwasser"
        risk_color = (196, 169, 77)  # yellow
    elif extrem.get("in_zone"):
        risk_label = "BETROFFEN — extremes Hochwasser"
        risk_color = (196, 169, 77)  # yellow (still serious but rare)
    else:
        risk_label = "NICHT BETROFFEN"
        risk_color = (91, 154, 111)  # green

    pdf.set_fill_color(*risk_color)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(fn, "B", 12)
    pdf.cell(80, 10, f"  {risk_label}", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Detailed table
    pdf.set_font(fn, "B", 8)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(50, 50, 50)
    w = [55, 50, 30, 55]
    pdf.cell(w[0], 6, "Szenario", border=1, fill=True)
    pdf.cell(w[1], 6, "Wiederkehr", border=1, fill=True)
    pdf.cell(w[2], 6, "Im Gebiet?", border=1, fill=True, align="C")
    pdf.cell(w[3], 6, "Bedeutung", border=1, fill=True)
    pdf.ln()

    rows = [
        (haeufig, "haeufiges Hochwasser", "T = 5 – 20 a", "haeufig wiederkehrend"),
        (hq100, "100-jaehriges Hochwasser", "T = 100 a", "Bemessungsereignis"),
        (extrem, "extremes Hochwasser", "≈ 1.5 × HQ100", "selten, aber moeglich"),
    ]

    pdf.set_font(fn, "", 8)
    for entry, label, period, meaning in rows:
        in_zone = entry.get("in_zone")
        if in_zone is True:
            mark, mark_color = "JA", (184, 84, 80)
        elif in_zone is False:
            mark, mark_color = "nein", (91, 154, 111)
        else:
            mark, mark_color = "n.a.", (150, 150, 150)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(w[0], 5, label, border=1)
        pdf.cell(w[1], 5, period, border=1)
        pdf.set_text_color(*mark_color)
        pdf.set_font(fn, "B", 8)
        pdf.cell(w[2], 5, mark, border=1, align="C")
        pdf.set_text_color(50, 50, 50)
        pdf.set_font(fn, "", 8)
        pdf.cell(w[3], 5, meaning, border=1)
        pdf.ln()

    pdf.ln(2)
    pdf.set_font(fn, "I", 7)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 3.5, (
        "Quelle: Bundesanstalt fuer Gewaesserkunde (BfG), nationale "
        "Hochwassergefahrenkarten gem. HWRM-Richtlinie 2007/60/EG, "
        "Datenstand 2. Zyklus (2016-2021), DL-DE/Zero-2.0. "
        "Detailliertere Karten bieten die Geoportale der jeweiligen "
        "Bundeslaender (z.B. ELWAS-WEB NRW, IÜG Bayern, hochwasser.baden-"
        "wuerttemberg.de). Die Auskunft ersetzt keine fachliche "
        "Hochwasserrisiko-Begutachtung."
    ))
    pdf.ln(2)


def _section_kostra(pdf: FPDF, fn: str, kostra_data: dict | None) -> None:
    """Render the "Niederschlag / Starkregen" section using KOSTRA-DWD-2020.

    Three states:
    - ``kostra_data is None`` or ``available is False`` → "Daten in
      Vorbereitung" (rasters not on disk yet)
    - some slot values present → table with values + buyer-friendly
      interpretation
    - all slots NODATA for this point → "kein KOSTRA-Wert fuer den
      Standort verfuegbar"
    """
    _section_header(pdf, fn, "5. Niederschlag / Starkregen (KOSTRA-DWD-2020)")
    pdf.set_font(fn, "", 9)
    pdf.set_text_color(80, 80, 80)

    if not kostra_data or not kostra_data.get("available"):
        pdf.multi_cell(0, 5, (
            "Starkregen-Statistiken aus KOSTRA-DWD-2020 (Deutscher Wetterdienst) "
            "werden zurzeit fuer diesen Standort vorbereitet. Die Daten zeigen, "
            "wie hoch der Regen waehrend eines extremen Ereignisses voraussichtlich "
            "ausfaellt — wichtig fuer die Einschaetzung von Keller- und "
            "Hangwasser-Risiken."
        ))
        pdf.ln(4)
        return

    slots = kostra_data.get("slots") or {}
    any_value = any(s.get("value") is not None for s in slots.values())

    if not any_value:
        pdf.multi_cell(0, 5, (
            "Fuer den abgefragten Punkt liegen keine KOSTRA-Niederschlagswerte vor. "
            "Das kann bei Off-Grid-Standorten (z.B. Hochgebirge, Inseln) vorkommen — "
            "regional verfuegbare Werte des naechstgelegenen Rasterpunkts liefert "
            "der DWD CDC OpenData-Server direkt."
        ))
        pdf.ln(4)
        return

    pdf.set_font(fn, "", 8)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(50, 50, 50)
    pdf.set_font(fn, "B", 8)
    w = [70, 30, 20, 70]
    pdf.cell(w[0], 6, "Bemessungsereignis", border=1, fill=True)
    pdf.cell(w[1], 6, "Niederschlag", border=1, fill=True, align="R")
    pdf.cell(w[2], 6, "Einheit", border=1, fill=True, align="C")
    pdf.cell(w[3], 6, "Bedeutung", border=1, fill=True)
    pdf.ln()

    pdf.set_font(fn, "", 8)
    for slot_name, entry in slots.items():
        label = entry.get("label", slot_name)
        unit = entry.get("unit", "mm")
        buyer = entry.get("buyer_text", "")
        value = entry.get("value")
        value_str = f"{value:.1f}" if isinstance(value, (int, float)) else "n.a."
        pdf.set_text_color(50, 50, 50)
        pdf.cell(w[0], 5, label, border=1)
        pdf.cell(w[1], 5, value_str, border=1, align="R")
        pdf.cell(w[2], 5, unit, border=1, align="C")
        pdf.cell(w[3], 5, buyer, border=1)
        pdf.ln()
    pdf.ln(2)

    pdf.set_font(fn, "I", 7)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 3.5, (
        "Quelle: DWD KOSTRA-DWD-2020, DOI 10.5676/DWD/KOSTRA-DWD-2020. "
        "Werte sind statistische Bemessungsniederschlaege (Wiederkehrintervall T) "
        "und ersetzen keine standortspezifische hydrologische Begutachtung."
    ))
    pdf.ln(2)


def _render_soil_directive(pdf: FPDF, fn: str, sd: dict) -> None:
    """Render the EU Soil Monitoring Directive 16-descriptor section."""
    _section_header(pdf, fn, "9. EU-Bodenueberwachungsrichtlinie 2025/2360")

    determined = sd.get("descriptors_determined", 0)
    total = sd.get("descriptors_total", 16)
    not_remote = sd.get("descriptors_not_remote", 0)
    overall = sd.get("overall_status", "keine_daten")
    cc = (sd.get("country_code") or "de").upper()

    pdf.set_font(fn, "", 9)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(0, 5, (
        f"Profil-Coverage Land {cc}: {determined} von {total} Descriptoren remote bestimmt, "
        f"{not_remote} erfordern In-situ-Beprobung (PFAS, PAK/PCB, Bodenbiodiversitaet, Mikrobiom). "
        f"Gesamtstatus: {_overall_label(overall)}."
    ))
    pdf.ln(3)

    pa = sd.get("part_a", {})
    pb = sd.get("part_b", {})
    pd_ = sd.get("part_d", {})

    rows = []
    er = pa.get("erosion_water") or {}
    if er:
        rows.append((
            "Wassererosion (RUSLE)",
            f"{er.get('value', '-')} t/ha/Jahr",
            er.get("status", "na"),
            f"R={er.get('r_factor', '-')} ({er.get('r_source', '-')})",
        ))
    ew = pa.get("erosion_wind") or {}
    if ew:
        rows.append(("Winderosion", ew.get("risk", "-"), ew.get("status", "na"), ew.get("note", "")))
    if pa.get("soc_pct") is not None:
        rows.append(("Org. Kohlenstoff (SOC)", f"{pa['soc_pct']} %",
                     pa.get("soc_status", "na"), "SoilGrids 250m"))
    if pa.get("ph") is not None:
        rows.append(("pH-Wert", f"{pa['ph']}", pa.get("ph_status", "na"), "SoilGrids 250m"))
    wr = pb.get("water_retention") or {}
    if wr.get("awc_mm_m") is not None:
        rows.append(("Wasserspeicherung (AWC)", f"{wr['awc_mm_m']} mm/m",
                     wr.get("status", "na"), wr.get("source", "")))
    sal = pb.get("salinisation") or {}
    if sal.get("ec_ds_m") is not None:
        rows.append(("Salinisierung", f"{sal['ec_ds_m']} dS/m",
                     sal.get("status", "na"), sal.get("source", "Regional-Schaetzung")))
    if pb.get("bulk_density_g_cm3") is not None:
        rows.append(("Lagerungsdichte", f"{pb['bulk_density_g_cm3']} g/cm³",
                     pb.get("bulk_density_status", "na"), "SoilGrids 250m"))
    if pd_.get("imperviousness_pct") is not None:
        rows.append(("Bodenversiegelung", f"{pd_['imperviousness_pct']} %",
                     "warn" if pd_["imperviousness_pct"] > 60 else "ok",
                     pd_.get("imperviousness_source", "HRL")))

    pdf.set_font(fn, "B", 8)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(50, 50, 50)
    w = [60, 35, 30, 65]
    pdf.cell(w[0], 6, "Descriptor", border=1, fill=True)
    pdf.cell(w[1], 6, "Wert", border=1, fill=True)
    pdf.cell(w[2], 6, "Status", border=1, fill=True)
    pdf.cell(w[3], 6, "Quelle", border=1, fill=True)
    pdf.ln()
    pdf.set_font(fn, "", 8)
    for label, value, status, source in rows:
        sr, sg, sb = _status_color(status)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(w[0], 5, label, border=1)
        pdf.cell(w[1], 5, value, border=1, align="R")
        pdf.set_text_color(sr, sg, sb)
        pdf.cell(w[2], 5, status, border=1, align="C")
        pdf.set_text_color(120, 120, 120)
        pdf.cell(w[3], 5, source, border=1)
        pdf.ln()
    pdf.ln(2)

    pdf.set_font(fn, "I", 7)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 3.5, (
        "Bewertet nach EU-Bodenueberwachungsrichtlinie (EU) 2025/2360. "
        "Schwellen DE: BBodSchV §8; NL: Circulaire bodemsanering 2013, Bijlage 1. "
        "Modellschaetzungen (RUSLE-Erosion, Salinisierung, AWC) sind in der "
        "Quellen-Spalte als solche gekennzeichnet."
    ))
    pdf.ln(3)


def _render_pesticides(pdf: FPDF, fn: str, p: dict) -> None:
    """Render the LUCAS NUTS2 pesticide-residues section."""
    _section_header(pdf, fn, "10. Pestizid-Rueckstaende (regional, NUTS2)")

    nuts2 = p.get("nuts2_code")
    n_det = p.get("n_detected", 0)
    flagged = p.get("flagged_legacy_count", 0)

    pdf.set_font(fn, "", 9)
    pdf.set_text_color(80, 80, 80)
    if nuts2 and n_det > 0:
        intro = (
            f"Im NUTS2-Gebiet {nuts2} ({p.get('nuts2_name', '')}) wurden in der "
            f"LUCAS-Topsoil-Stichprobe 2018 insgesamt {n_det} Pestizid-Wirkstoffe "
            f"oberhalb der Bestimmungsgrenze nachgewiesen"
        )
        if flagged > 0:
            intro += f", davon {flagged} Substanzen aus der EU-Verbotsliste (Legacy)"
        pdf.multi_cell(0, 5, intro + ".")
    elif nuts2:
        pdf.multi_cell(0, 5, (
            f"Im NUTS2-Gebiet {nuts2} ({p.get('nuts2_name', '')}) wurden in der "
            "LUCAS-Topsoil-Stichprobe 2018 keine Pestizid-Rueckstaende oberhalb der "
            "Bestimmungsgrenze nachgewiesen."
        ))
    else:
        pdf.multi_cell(0, 5, "Kein LUCAS-Pestizid-Datensatz fuer diese Region verfuegbar.")
    pdf.ln(2)

    top = p.get("top_substances") or []
    if top:
        pdf.set_font(fn, "B", 8)
        pdf.set_fill_color(240, 240, 240)
        pdf.set_text_color(50, 50, 50)
        w = [80, 45, 65]
        pdf.cell(w[0], 6, "Substanz", border=1, fill=True)
        pdf.cell(w[1], 6, "Konzentration", border=1, fill=True, align="R")
        pdf.cell(w[2], 6, "Hinweis", border=1, fill=True)
        pdf.ln()
        pdf.set_font(fn, "", 8)
        for s in top:
            pdf.set_text_color(50, 50, 50)
            pdf.cell(w[0], 5, s.get("name", ""), border=1)
            pdf.cell(w[1], 5, f"{s.get('concentration_mg_kg', 0)} mg/kg", border=1, align="R")
            note = "EU-Verbotsliste" if s.get("flagged_legacy") else "Aktuell zugelassen"
            if s.get("flagged_legacy"):
                pdf.set_text_color(184, 84, 80)
            else:
                pdf.set_text_color(120, 120, 120)
            pdf.cell(w[2], 5, note, border=1)
            pdf.ln()
        pdf.ln(2)

    pdf.set_font(fn, "I", 7)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 3.5, (
        "Quelle: LUCAS Topsoil 2018 (JRC ESDAC), aggregiert auf NUTS2. "
        "Konzentrationen sind regionale Mittelwerte und beziehen sich nicht "
        "auf das einzelne Grundstueck. BBodSchV definiert keine direkten "
        "Boden-Schwellenwerte fuer moderne Pflanzenschutzmittel; die "
        "EU-Trinkwasser-Schwelle 0,1 µg/L dient hier nur als Groessenordnung."
    ))
    pdf.ln(3)


def _render_slope(pdf: FPDF, fn: str, s: dict) -> None:
    """Render the Geländeprofil section: elevation, slope, aspect.

    Slope is also fed into the RUSLE LS-factor calculation in the EU
    Soil Directive section above. Showing it here separately gives the
    buyer an explicit terrain read for build/extension planning.
    """
    _section_header(pdf, fn, "8. Gelaendeprofil")

    cls = s.get("classification", "")
    slope_deg = s.get("slope_deg", 0)
    color_map = {
        "flach": (91, 154, 111),
        "leicht geneigt": (170, 190, 90),
        "Hanglage": (196, 169, 77),
        "Steilhang": (184, 84, 80),
    }
    r, g, b = color_map.get(cls, (150, 150, 150))
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(fn, "B", 11)
    pdf.cell(80, 9, f"  {cls.upper()} ({slope_deg}°)", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_text_color(50, 50, 50)
    _kpi_row(pdf, fn, [
        (f"{s.get('elevation_m', '-')} m", "Höhe NN"),
        (f"{slope_deg}°", "Hangneigung"),
        (s.get("aspect_label", "-"), f"Expositionsrichtung ({int(s.get('aspect_deg', 0))}°)"),
    ])
    pdf.ln(2)

    pdf.set_font(fn, "", 9)
    pdf.set_text_color(80, 80, 80)
    interpretation = {
        "flach": "Flaches Gelaende — keine besonderen Erosions- oder Hangrutschungs-Risiken aus der Topographie.",
        "leicht geneigt": "Leicht geneigtes Gelaende — moderate Wasser-Erosionsrisiken bei sandigen oder schluffigen Boeden, aber baulich unkritisch.",
        "Hanglage": "Hanglage — erhoehtes Risiko fuer Wassererosion, Boden-Setzungen und Hang-Stabilitaet bei Bau-Massnahmen. Die Hangneigung fliesst in das RUSLE-Erosionsmodell der naechsten Sektion ein.",
        "Steilhang": "Steilhang — signifikante Risiken fuer Erosion, Hangrutsch und Setzungen. Statisches Bodengutachten fuer jede Bau-Massnahme dringend empfohlen.",
    }.get(cls, "Topographie-Klassifikation auf Basis SRTM-Hoehendaten.")
    pdf.multi_cell(0, 5, interpretation)
    pdf.ln(2)

    pdf.set_font(fn, "I", 7)
    pdf.set_text_color(120, 120, 120)
    scale = s.get("scale_m", 50)
    src = s.get("source", "")
    pdf.multi_cell(0, 3.5, (
        f"Quelle: {src}. Multi-Scale-Sampling (50/150/500 m), groesste Steigung "
        f"bei {scale} m gewaehlt. Vertikale Aufloesung ~5-10 m, horizontale ~30 m."
    ))
    pdf.ln(3)


def _render_altlasten(pdf: FPDF, fn: str, a: dict) -> None:
    """Render the Altlasten / land-use-proxy section.

    Two flavors driven by ``data_kind``:
      - 'behoerden-kataster' (NL via PDOK): real cataster hits
      - 'land-use-indikator' (DE via CORINE proxy): land-use risk codes
        + pointer to authority enquiry
    """
    _section_header(pdf, fn, "11. Altlasten / Bodenkontamination")

    kind = a.get("data_kind", "")
    risk = a.get("risk", "gruen")
    sites = a.get("sites") or []

    # Risk badge
    r, g, b = _ampel_color({"gruen": "gruen", "gelb": "gelb", "rot": "rot"}.get(risk, "gruen"))
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(fn, "B", 11)
    label = {
        "gruen": "  KEIN BEFUND IM 200 m UMFELD",
        "gelb": "  HINWEIS-BEFUND IM 200 m UMFELD",
        "rot": "  AKTIVE KONTAMINATION GEMELDET",
    }.get(risk, "  KEINE DATEN")
    pdf.cell(120, 9, label, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_text_color(80, 80, 80)
    pdf.set_font(fn, "", 9)

    if kind == "behoerden-kataster":
        # NL — PDOK Bodemloket
        pdf.multi_cell(0, 5, (
            f"Datenquelle: {a.get('source', 'PDOK Bodemloket')}. "
            "Adress-genaue Wbb-Lokationen aus der nationalen niederlaendischen "
            "Datenbank fuer Bodensanierungsfaelle."
        ))
        pdf.ln(2)
        if sites:
            pdf.set_font(fn, "B", 8)
            pdf.set_fill_color(240, 240, 240)
            pdf.set_text_color(50, 50, 50)
            w = [55, 50, 35, 50]
            pdf.cell(w[0], 6, "Locatie", border=1, fill=True)
            pdf.cell(w[1], 6, "Type", border=1, fill=True)
            pdf.cell(w[2], 6, "Status", border=1, fill=True, align="C")
            pdf.cell(w[3], 6, "Quelle", border=1, fill=True)
            pdf.ln()
            pdf.set_font(fn, "", 8)
            for s in sites[:8]:
                pdf.set_text_color(50, 50, 50)
                pdf.cell(w[0], 5, str(s.get("name", ""))[:30], border=1)
                pdf.cell(w[1], 5, str(s.get("site_type", ""))[:25], border=1)
                pdf.cell(w[2], 5, str(s.get("status", "")), border=1, align="C")
                pdf.cell(w[3], 5, str(s.get("source", ""))[:28], border=1)
                pdf.ln()
        else:
            pdf.set_text_color(120, 120, 120)
            pdf.cell(0, 5, "Keine Wbb-Lokationen im 200 m-Umfeld registriert.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    elif kind == "land-use-indikator":
        # DE — CORINE proxy + authority enquiry hint
        pdf.multi_cell(0, 5, (
            f"Datenquelle: {a.get('source', 'CORINE Land Cover 2018')}. "
            "Land-Use-Indikator auf 100 m-Raster, 5-Punkt-Sampling im "
            "100-150 m-Umfeld. KEIN Behoerdenkataster."
        ))
        pdf.ln(2)
        if sites:
            pdf.set_font(fn, "B", 8)
            pdf.set_fill_color(240, 240, 240)
            pdf.set_text_color(50, 50, 50)
            w = [15, 50, 30, 95]
            pdf.cell(w[0], 6, "CLC", border=1, fill=True, align="C")
            pdf.cell(w[1], 6, "Klasse", border=1, fill=True)
            pdf.cell(w[2], 6, "Distanz (ca.)", border=1, fill=True, align="C")
            pdf.cell(w[3], 6, "Begruendung", border=1, fill=True)
            pdf.ln()
            pdf.set_font(fn, "", 8)
            for s in sites:
                pdf.set_text_color(50, 50, 50)
                pdf.cell(w[0], 5, str(s.get("code", "")), border=1, align="C")
                pdf.cell(w[1], 5, str(s.get("label", ""))[:28], border=1)
                pdf.cell(w[2], 5, f"{int(s.get('distance_m', 0))} m", border=1, align="C")
                pdf.cell(w[3], 5, str(s.get("reason", ""))[:55], border=1)
                pdf.ln()
        else:
            pdf.set_text_color(120, 120, 120)
            pdf.cell(0, 5, "Im 100-150 m-Umfeld keine kontaminations-korrelierten Land-Use-Klassen.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        # Authority-enquiry hint — only for DE
        if a.get("offer_authority_request"):
            pdf.set_fill_color(248, 248, 248)
            pdf.set_draw_color(220, 220, 220)
            pdf.rect(10, pdf.get_y(), 190, 18, "FD")
            pdf.set_xy(13, pdf.get_y() + 2)
            pdf.set_font(fn, "B", 8)
            pdf.set_text_color(40, 40, 40)
            pdf.cell(0, 4, "Rechtsverbindliche Behoerdenauskunft anfordern", new_x="LMARGIN", new_y="NEXT")
            pdf.set_x(13)
            pdf.set_font(fn, "", 7)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(184, 3.5, (
                "Adress-genaue Altlasten-Daten in DE sind oeffentlich nicht abrufbar (LUBW ALTIS / "
                "LANUV FIS AlBo geschuetzt). Wir koennen die Anfrage in Ihrem Auftrag beim "
                "zustaendigen Bauamt stellen — Kontakt: altlasten@geoforensic.de."
            ))
            pdf.ln(3)

    pdf.set_font(fn, "I", 7)
    pdf.set_text_color(120, 120, 120)
    note = a.get("note") or ""
    if note:
        pdf.multi_cell(0, 3.5, f"Hinweis: {note}")
    pdf.ln(3)


def _overall_label(s: str) -> str:
    return {
        "gesund": "GESUND",
        "bedingt": "BEDINGT",
        "ungesund": "UNGESUND",
        "keine_daten": "KEINE DATEN",
    }.get(s, s.upper())


def _section_header(pdf: FPDF, fn: str, title: str):
    pdf.set_draw_color(34, 197, 94)
    pdf.set_line_width(0.8)
    pdf.line(10, pdf.get_y(), 60, pdf.get_y())
    pdf.ln(2)
    pdf.set_font(fn, "B", 12)
    pdf.set_text_color(15, 32, 64)
    pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _kpi_row(pdf: FPDF, fn: str, items: list[tuple[str, str]]):
    pdf.set_draw_color(220, 220, 220)
    pdf.set_fill_color(248, 248, 248)
    y = pdf.get_y()
    col_w = 190 / len(items)
    pdf.rect(10, y, 190, 24, "FD")
    for i, (val, label) in enumerate(items):
        x = 10 + i * col_w
        pdf.set_xy(x, y + 2)
        pdf.set_font(fn, "B", 13)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(col_w, 10, val, align="C")
        pdf.set_xy(x, y + 13)
        pdf.set_font(fn, "", 7)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(col_w, 6, label, align="C")
    pdf.set_y(y + 28)


def _assess_soilgrid(prop: str, val: float) -> str:
    if prop == "phh2o":
        if 5.5 <= val <= 7.5:
            return "ok"
        return "warn" if 4.5 <= val <= 8.5 else "critical"
    if prop == "soc":
        if val >= 20:
            return "ok"
        return "warn" if val >= 10 else "critical"
    if prop == "bdod":
        if val < 1.5:
            return "ok"
        return "warn" if val < 1.7 else "critical"
    return "ok"


def _classify_texture(clay: float, sand: float, silt: float) -> str:
    if sand > 65:
        return "Sandboden (leicht, durchlaessig)"
    if clay > 40:
        return "Tonboden (schwer, wasserrueckhaltend)"
    if silt > 60:
        return "Schluffboden (erosionsanfaellig)"
    if 20 <= clay <= 35 and 20 <= sand <= 50:
        return "Lehmboden (ideal, ausgewogen)"
    return "Mischboden"
