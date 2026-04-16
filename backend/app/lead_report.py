"""Generate a personalized mini-report PDF based on quiz answers + EGMS data.

Uses Arial TTF (system font) for proper German Umlaut rendering.
Brand: "Bodenbericht" (Gregor's marketing brand).
"""

import os
from datetime import datetime, timezone

from fpdf import FPDF

# ── System font path (Windows: C:/Windows/Fonts, Docker: /usr/share/fonts) ──
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


# ── Texte je nach Quiz-Antworten ────────────────────────────────────

_NUTZUNG_TEXT = {
    "Eigenheim / Garten": (
        "Als Eigenheimbesitzer ist die Stabilität Ihres Bodens besonders wichtig "
        "für den langfristigen Werterhalt Ihrer Immobilie und die Sicherheit "
        "Ihrer Familie."
    ),
    "Landwirtschaft": (
        "Für landwirtschaftliche Nutzung ist die Bodenqualität und -stabilität "
        "entscheidend für Ertragssicherheit und nachhaltige Bewirtschaftung."
    ),
    "Ich plane einen Hauskauf": (
        "Vor einem Grundstückskauf ist ein Bodenscreening besonders wichtig: "
        "Versteckte Bodenbewegungen können zu erheblichen Sanierungskosten "
        "führen, die im Kaufpreis nicht berücksichtigt sind."
    ),
    "Gewerblich": (
        "Bei gewerblicher Nutzung sind Bodenstabilität und mögliche Altlasten "
        "relevant für Baugenehmigungen, Versicherungsprämien und Haftungsfragen."
    ),
}

_BEDENKEN_TEXT_DE = {
    "Ja, Altlasten oder gesundheitliche Bedenken": (
        "Ihre Bedenken bezüglich Altlasten sind berechtigt — in Deutschland "
        "sind über 300.000 altlastenverdächtige Flächen registriert. "
        "Die Satellitendaten zeigen, ob Ihr Standort von Bodenbewegungen "
        "betroffen ist, die auf unterirdische Hohlräume oder Setzungen hindeuten."
    ),
    "Ja, schlechtes Pflanzenwachstum": (
        "Schlechtes Pflanzenwachstum kann auf Bodenveränderungen hinweisen. "
        "Bodenbewegungen beeinflussen die Wasserführung und können "
        "auf kontaminierte Untergründe oder veränderte Grundwasserspiegel hindeuten."
    ),
    "Nein, ich möchte nur auf Nummer sicher gehen": (
        "Vorsorge ist der beste Schutz. Ein Screening zeigt Ihnen, ob an Ihrem "
        "Standort Auffälligkeiten vorliegen — bevor daraus ein Problem wird."
    ),
}

_BEDENKEN_TEXT_NL = {
    "Ja, Altlasten oder gesundheitliche Bedenken": (
        "Ihre Bedenken sind berechtigt — in den Niederlanden sind zahlreiche "
        "Standorte mit historischen Bodenbelastungen dokumentiert. "
        "Die Satellitendaten zeigen, ob Ihr Standort von Bodenbewegungen "
        "betroffen ist, die auf Setzungen oder Fundierungsprobleme hindeuten."
    ),
    "Ja, schlechtes Pflanzenwachstum": (
        "Schlechtes Pflanzenwachstum kann auf Bodenveränderungen hinweisen. "
        "In den Niederlanden sind Setzungen durch niedrige Grundwasserstände "
        "und weiche Böden ein häufiges Phänomen."
    ),
    "Nein, ich möchte nur auf Nummer sicher gehen": (
        "Vorsorge ist der beste Schutz. Seit April 2026 ist in den Niederlanden "
        "ein Funderingslabel bei jeder Immobilienbewertung Pflicht — "
        "ein Bodenscreening gibt Ihnen zusätzliche Sicherheit."
    ),
}

_DRINGLICHKEIT = {
    "Sofort – es eilt": (
        "Handlungsempfehlung: Bei erhöhten Werten empfehlen wir eine zeitnahe "
        "Begutachtung durch einen Sachverständigen. Wir vermitteln Ihnen "
        "gerne einen zertifizierten Experten in Ihrer Region."
    ),
    "Innerhalb der nächsten 2 Wochen": (
        "Handlungsempfehlung: Planen Sie bei auffälligen Werten eine "
        "weiterführende Untersuchung innerhalb der nächsten Wochen ein."
    ),
    "Ich informiere mich nur": (
        "Handlungsempfehlung: Beobachten Sie die Entwicklung. "
        "Wir empfehlen eine erneute Prüfung in 6–12 Monaten."
    ),
}


def _ampel_color(ampel: str) -> tuple[int, int, int]:
    return {"gruen": (34, 197, 94), "gelb": (234, 179, 8), "rot": (239, 68, 68)}.get(ampel, (150, 150, 150))


def _ampel_label(ampel: str) -> str:
    return {"gruen": "UNAUFFÄLLIG", "gelb": "AUFFÄLLIG", "rot": "KRITISCH"}.get(ampel, "KEINE DATEN")


def _ampel_bewertung(ampel: str) -> str:
    return {
        "gruen": (
            "Im Untersuchungsradius wurden keine auffälligen Bodenbewegungen "
            "gemessen. Die Lage ist stabil. Es besteht kein akuter Handlungsbedarf."
        ),
        "gelb": (
            "Im Untersuchungsradius wurden vereinzelt erhöhte Bodenbewegungen "
            "gemessen. Eine weitere Beobachtung oder stichprobenartige "
            "Überprüfung wird empfohlen."
        ),
        "rot": (
            "Im Untersuchungsradius wurden kritische Bodenbewegungen gemessen. "
            "Eine fachliche Einschätzung durch einen qualifizierten Gutachter "
            "ist dringend angeraten."
        ),
    }.get(ampel, "Für diesen Standort liegen aktuell keine Satellitendaten vor.")


def _detect_country(address: str) -> str:
    """Guess country from address string."""
    lower = address.lower()
    if "nederland" in lower or "netherlands" in lower or "amsterdam" in lower or "rotterdam" in lower or "den haag" in lower:
        return "NL"
    return "DE"


def generate_lead_report(
    address: str,
    lat: float,
    lon: float,
    ampel: str,
    point_count: int,
    mean_velocity: float,
    max_velocity: float,
    geo_score: int | None,
    answers: dict,
) -> bytes:
    """Generate a personalized mini-report PDF for a quiz lead."""
    nutzung = answers.get("nutzung", "")
    bedenken = answers.get("bedenken", "")
    dringlichkeit = answers.get("dringlichkeit", "")
    country = _detect_country(address)
    now = datetime.now(timezone.utc)
    has_data = point_count > 0

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Register Unicode font
    font_regular = _find_font(_FONT_PATHS)
    font_bold = _find_font(_FONT_BOLD_PATHS)
    if font_regular:
        pdf.add_font("Report", "", font_regular)
        pdf.add_font("Report", "B", font_bold or font_regular)
        pdf.add_font("Report", "I", font_regular)  # italic fallback
        fn = "Report"
    else:
        fn = "Helvetica"

    pdf.add_page()

    # ── Header ──────────────────────────────────────────────────────
    pdf.set_fill_color(15, 32, 64)  # dark navy
    pdf.rect(0, 0, 210, 38, "F")

    pdf.set_text_color(255, 255, 255)
    pdf.set_font(fn, "B", 26)
    pdf.set_y(10)
    pdf.cell(0, 10, "BODENBERICHT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fn, "", 10)
    pdf.set_text_color(180, 200, 220)
    pdf.cell(0, 6, "Standort-Risikoeinschätzung", align="C", new_x="LMARGIN", new_y="NEXT")

    # Green accent line
    pdf.set_draw_color(34, 197, 94)
    pdf.set_line_width(1.5)
    pdf.line(10, 40, 200, 40)
    pdf.set_y(45)

    # ── Standort ────────────────────────────────────────────────────
    pdf.set_text_color(30, 30, 30)
    pdf.set_font(fn, "B", 13)
    pdf.multi_cell(0, 7, address)
    pdf.set_font(fn, "", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 5, f"{lat:.5f}, {lon:.5f}  |  {now.strftime('%d.%m.%Y %H:%M')} UTC", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # ── Ampel Badge ─────────────────────────────────────────────────
    r, g, b = _ampel_color(ampel)
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(fn, "B", 16)
    label = _ampel_label(ampel) if has_data else "KEINE DATEN"
    pdf.cell(80, 14, f"  {label}", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # ── KPI Box ─────────────────────────────────────────────────────
    pdf.set_draw_color(220, 220, 220)
    pdf.set_fill_color(248, 248, 248)
    y_start = pdf.get_y()
    pdf.rect(10, y_start, 190, 28, "FD")

    pdf.set_text_color(30, 30, 30)
    col_w = 47.5
    pdf.set_xy(10, y_start + 3)
    for val, label in [
        (str(point_count), "Messpunkte"),
        (f"{mean_velocity:.1f} mm/a" if has_data else "–", "Mittlere Geschw."),
        (f"{max_velocity:.1f} mm/a" if has_data else "–", "Max. Geschw."),
        (f"{geo_score}/100" if geo_score is not None else "–", "GeoScore"),
    ]:
        x = pdf.get_x()
        pdf.set_font(fn, "B", 14)
        pdf.cell(col_w, 10, val, align="C")
        pdf.set_xy(x, y_start + 15)
        pdf.set_font(fn, "", 7)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(col_w, 6, label, align="C")
        pdf.set_xy(x + col_w, y_start + 3)
        pdf.set_text_color(30, 30, 30)

    pdf.set_y(y_start + 34)

    # ── Bewertung ───────────────────────────────────────────────────
    pdf.set_font(fn, "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, "Bewertung", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fn, "", 10)
    pdf.multi_cell(0, 5, _ampel_bewertung(ampel))
    pdf.ln(4)

    # ── Personalisierte Einschätzung ────────────────────────────────
    pdf.set_font(fn, "B", 12)
    pdf.cell(0, 8, "Ihre individuelle Einschätzung", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fn, "", 10)

    nutzung_text = _NUTZUNG_TEXT.get(nutzung, "")
    if nutzung_text:
        pdf.multi_cell(0, 5, nutzung_text)
        pdf.ln(2)

    bedenken_texts = _BEDENKEN_TEXT_NL if country == "NL" else _BEDENKEN_TEXT_DE
    bedenken_text = bedenken_texts.get(bedenken, "")
    if bedenken_text:
        pdf.multi_cell(0, 5, bedenken_text)
        pdf.ln(2)

    dringlichkeit_text = _DRINGLICHKEIT.get(dringlichkeit, "")
    if dringlichkeit_text:
        pdf.set_font(fn, "B", 10)
        pdf.multi_cell(0, 5, dringlichkeit_text)
        pdf.set_font(fn, "", 10)
        pdf.ln(4)

    # ── Datenquellen ────────────────────────────────────────────────
    pdf.set_font(fn, "B", 11)
    pdf.cell(0, 8, "Geprüfte Datenquellen", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fn, "", 9)

    sources = [
        (True, "Copernicus EGMS L3 Ortho (Sentinel-1, 2019–2022)"),
        (True, "Nominatim / OpenStreetMap (Geocodierung)"),
        (False, "Hochwasser-Gefahrenkarten (in Vorbereitung)"),
        (False, "Altlastenkataster (in Vorbereitung)"),
    ]
    if country == "NL":
        sources.append((False, "Funderingslabel-Daten KCAF (in Vorbereitung)"))

    for active, name in sources:
        marker = "+" if active else "-"
        pdf.set_text_color(34, 197, 94) if active else pdf.set_text_color(180, 180, 180)
        pdf.set_font(fn, "B", 10)
        pdf.cell(8, 5, marker)
        pdf.set_text_color(60, 60, 60) if active else pdf.set_text_color(150, 150, 150)
        pdf.set_font(fn, "", 9)
        pdf.cell(0, 5, name, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)

    # ── Disclaimer ──────────────────────────────────────────────────
    pdf.set_draw_color(220, 220, 220)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)
    pdf.set_font(fn, "I", 7)
    pdf.set_text_color(130, 130, 130)
    pdf.multi_cell(0, 3.5, (
        "Hinweis: Diese Risikoeinschätzung ist ein automatisiertes Datenscreening "
        "auf Basis von InSAR-Satellitendaten (Copernicus EGMS) und ersetzt keine "
        "Ortsbesichtigung oder fachliche Einzelfallbewertung durch einen "
        "zugelassenen Sachverständigen. "
        "Generated using European Union's Copernicus Land Monitoring Service information."
    ))

    pdf.ln(3)
    pdf.set_font(fn, "", 7)
    pdf.set_text_color(170, 170, 170)
    pdf.cell(0, 4, f"© Bodenbericht {now.year} | bodenbericht.de", new_x="LMARGIN", new_y="NEXT")

    return pdf.output()
