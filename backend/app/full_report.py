"""Full Bodenbericht PDF — all data sources combined.

Sections:
1. Header + Address + Ampel Badge
2. Bodenbewegung (EGMS InSAR)
3. Schwermetalle (LUCAS Topsoil) + BBodSchV Vergleich
4. Bodenqualitaet (SoilGrids: pH, SOC, Textur, Dichte)
5. Regionale Pestizid-Belastung (LUCAS Pesticide Module, NUTS2)
6. Personalisierte Einschaetzung (Quiz-Antworten)
7. Datenquellen + Disclaimer

Naehrstoffe (P, N from LUCAS) are currently folded into the Schwermetall-
pipeline on the data side but not yet printed as a standalone section in
this PDF flavour — flag, not a blocker.
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
) -> bytes:
    """Generate a comprehensive Bodenbericht PDF."""
    answers = answers or {}
    now = datetime.now(timezone.utc)
    has_egms = point_count > 0
    soilgrids = soil_profile.get("soilgrids", {})
    metals = soil_profile.get("metals", {})
    metal_status = soil_profile.get("metal_status", {})
    nutrients = soil_profile.get("nutrients", {})
    pesticides = soil_profile.get("pesticides", {})
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
    # PAGE 2: Soil quality + Nutrients + Personalization
    # ════════════════════════════════════════════════════════════════
    pdf.add_page()

    # ── Section: Bodenqualitaet ─────────────────────────────────────
    _section_header(pdf, fn, "3. Bodenqualitaet (SoilGrids 250m)")

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
    _section_header(pdf, fn, "4. Naehrstoffe")

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

    # ── Section: Regionale Pestizid-Belastung ───────────────────────
    if pesticides and pesticides.get("top_substances"):
        _section_header(pdf, fn, "5. Regionale Pestizid-Belastung (NUTS2)")
        pdf.set_font(fn, "", 8)
        pdf.set_text_color(100, 100, 100)
        region = pesticides.get("nuts2", "?")
        total = pesticides.get("total_detected", 0)
        percentile = pesticides.get("regional_percentile")
        ctx = f"NUTS2-Region {region} - {total} Substanzen nachgewiesen"
        if percentile is not None:
            ctx += f" - Region liegt im {percentile}. Perzentil DE-weit"
        pdf.cell(0, 4, ctx, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        pdf.set_font(fn, "B", 8)
        pdf.set_fill_color(240, 240, 240)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(95, 6, "Substanz (Top 10)", border=1, fill=True)
        pdf.cell(35, 6, "Konzentration", border=1, fill=True, align="R")
        pdf.cell(30, 6, "DE-Perzentil", border=1, fill=True, align="C")
        pdf.ln()
        pdf.set_font(fn, "", 8)
        for sub in pesticides["top_substances"][:10]:
            name = str(sub["name"])[:60]
            val = sub["value_mg_kg"]
            p = sub.get("percentile_national")
            pdf.set_text_color(50, 50, 50)
            pdf.cell(95, 5, name, border=1)
            pdf.cell(35, 5, f"{val:.4f}", border=1, align="R")
            pdf.cell(30, 5, f"{p}" if p is not None else "-", border=1, align="C")
            pdf.ln()
        pdf.set_font(fn, "", 7)
        pdf.set_text_color(120, 120, 120)
        pdf.ln(1)
        pdf.cell(0, 4, "Quelle: LUCAS Topsoil Survey Pesticide Module (ESDAC), aggregiert auf NUTS2-Ebene.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # ── Section: Individuelle Einschaetzung ─────────────────────────
    if answers:
        _section_header(pdf, fn, "6. Ihre individuelle Einschaetzung")
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
    sources = [
        (has_egms, "Copernicus EGMS L3 Ortho (Sentinel-1, 2019-2022)"),
        (True, "Nominatim / OpenStreetMap (Geocodierung)"),
        (bool(metals), "LUCAS Topsoil Survey (Schwermetalle, Naehrstoffe)"),
        (bool(pesticides), "LUCAS Topsoil Pesticide Module (NUTS2-Ebene, ESDAC)"),
        (bool(soilgrids.get("phh2o")), "SoilGrids 250m (pH, SOC, Textur, Dichte)"),
        (False, "Hochwasser-Gefahrenkarten (in Vorbereitung)"),
        (False, "Altlastenkataster (in Vorbereitung)"),
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
