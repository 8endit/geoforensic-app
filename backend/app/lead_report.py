"""Generate a personalized mini-report PDF based on quiz answers + EGMS data."""

from datetime import datetime, timezone

from fpdf import FPDF


# ── Bewertungstexte je nach Quiz-Antworten ────────────────────────────

_NUTZUNG_TEXT = {
    "Eigenheim / Garten": (
        "Als Eigenheimbesitzer ist die Stabilität Ihres Bodens besonders wichtig "
        "für den langfristigen Werterhalt Ihrer Immobilie und die Sicherheit Ihrer Familie."
    ),
    "Landwirtschaft": (
        "Für landwirtschaftliche Nutzung ist die Bodenqualität und -stabilität "
        "entscheidend für Ertragssicherheit und nachhaltige Bewirtschaftung."
    ),
    "Ich plane einen Hauskauf": (
        "Vor einem Grundstückskauf ist ein Bodenscreening besonders wichtig: "
        "Versteckte Bodenbewegungen können zu erheblichen Sanierungskosten führen, "
        "die im Kaufpreis nicht berücksichtigt sind."
    ),
    "Gewerblich": (
        "Bei gewerblicher Nutzung sind Bodenstabilität und mögliche Altlasten "
        "relevant für Baugenehmigungen, Versicherungsprämien und Haftungsfragen."
    ),
}

_BEDENKEN_TEXT = {
    "Ja, Altlasten oder gesundheitliche Bedenken": (
        "Ihre Bedenken bezüglich Altlasten sind berechtigt — in Deutschland sind "
        "über 300.000 altlastenverdächtige Flächen registriert. "
        "Die Satellitendaten zeigen, ob Ihr Standort von Bodenbewegungen betroffen ist, "
        "die auf unterirdische Hohlräume oder Setzungen hindeuten."
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

_DRINGLICHKEIT_EMPFEHLUNG = {
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
    return {
        "gruen": (34, 197, 94),
        "gelb": (234, 179, 8),
        "rot": (239, 68, 68),
    }.get(ampel, (100, 100, 100))


def _ampel_label(ampel: str) -> str:
    return {
        "gruen": "UNAUFFAELLIG",
        "gelb": "AUFFAELLIG",
        "rot": "KRITISCH",
    }.get(ampel, "KEINE DATEN")


def _ampel_bewertung(ampel: str) -> str:
    return {
        "gruen": (
            "Im Untersuchungsradius wurden keine auffaelligen Bodenbewegungen gemessen. "
            "Die Lage ist stabil. Es besteht kein akuter Handlungsbedarf."
        ),
        "gelb": (
            "Im Untersuchungsradius wurden vereinzelt erhoehte Bodenbewegungen gemessen. "
            "Eine weitere Beobachtung oder stichprobenartige Ueberpruefung wird empfohlen."
        ),
        "rot": (
            "Im Untersuchungsradius wurden kritische Bodenbewegungen gemessen. "
            "Eine fachliche Einschaetzung durch einen qualifizierten Gutachter ist dringend angeraten."
        ),
    }.get(ampel, "Fuer diesen Standort liegen aktuell keine Satellitendaten vor.")


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
    now = datetime.now(timezone.utc)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # ── Header ──
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 10, "BODENBERICHT", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "Kostenlose Risikoeinschaetzung", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(16, 185, 129)
    pdf.set_line_width(1)
    pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2)
    pdf.ln(8)

    # ── Standort ──
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, address, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"Koordinaten: {lat:.5f}, {lon:.5f}  |  Erstellt: {now.strftime('%d.%m.%Y %H:%M UTC')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # ── Ampel Badge ──
    r, g, b = _ampel_color(ampel)
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(70, 14, _ampel_label(ampel), fill=True, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # ── KPIs ──
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    kpis = [
        f"Messpunkte im Radius: {point_count}",
        f"Mittlere Geschwindigkeit: {mean_velocity:.2f} mm/a" if point_count > 0 else "Mittlere Geschwindigkeit: keine Daten",
        f"Maximale Geschwindigkeit: {max_velocity:.2f} mm/a" if point_count > 0 else "Maximale Geschwindigkeit: keine Daten",
        f"GeoScore: {geo_score}/100" if geo_score is not None else "GeoScore: nicht verfuegbar",
    ]
    for kpi in kpis:
        pdf.cell(0, 6, kpi, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── Bewertung ──
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Bewertung", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, _ampel_bewertung(ampel))
    pdf.ln(4)

    # ── Personalisierter Kontext (basierend auf Quiz-Antworten) ──
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Ihre individuelle Einschaetzung", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)

    nutzung_text = _NUTZUNG_TEXT.get(nutzung, "")
    if nutzung_text:
        pdf.multi_cell(0, 5, nutzung_text)
        pdf.ln(2)

    bedenken_text = _BEDENKEN_TEXT.get(bedenken, "")
    if bedenken_text:
        pdf.multi_cell(0, 5, bedenken_text)
        pdf.ln(2)

    dringlichkeit_text = _DRINGLICHKEIT_EMPFEHLUNG.get(dringlichkeit, "")
    if dringlichkeit_text:
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(0, 5, dringlichkeit_text)
        pdf.ln(4)

    # ── Datenquellen ──
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Datenquellen", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    sources = [
        "[x] Copernicus EGMS L3 Ortho (Sentinel-1, 2019-2022)",
        "[x] Nominatim / OpenStreetMap (Geocodierung)",
        "[ ] Hochwasser-Gefahrenkarten (in Vorbereitung)",
        "[ ] Altlastenkataster (in Vorbereitung)",
    ]
    for src in sources:
        pdf.cell(0, 5, f"  {src}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── Disclaimer ──
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 4, (
        "Hinweis: Diese kostenlose Risikoeinschaetzung ist ein automatisiertes "
        "Datenscreening auf Basis von InSAR-Satellitendaten (Copernicus EGMS) und "
        "ersetzt keine Ortsbesichtigung oder fachliche Einzelfallbewertung durch "
        "einen zugelassenen Sachverstaendigen. "
        "Generated using European Union's Copernicus Land Monitoring Service information."
    ))

    pdf.ln(3)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, f"(c) Bodenbericht {now.year} | geoforensic.de", new_x="LMARGIN", new_y="NEXT")

    return pdf.output()
