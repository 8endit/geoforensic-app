"""PDF report generation using WeasyPrint."""

from html import escape

from app.models import Report


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ── Geprüfte Datenquellen (hardcoded, flip status when a source goes live) ──

_DATA_SOURCES = [
    ("aktiv", "EGMS Ortho L3 (Copernicus)", "Vertikale + Ost-West Bodenbewegung, 2015–2022"),
    ("aktiv", "Nominatim / OpenStreetMap", "Geocodierung der Eingabeadresse"),
    ("geplant", "BGR Bodenbewegungsdienst", "Hochauflösende nationale InSAR-Daten (DE)"),
    ("geplant", "Hochwasser-Gefahrenkarten", "EU-HWRL Fluss-/Küstenhochwasser"),
    ("geplant", "Altlastenkataster", "Kontaminierte Standorte (DE: LGRB / NL: Bodemloket)"),
    ("geplant", "bodemdalingskaart.nl (SkyGeo)", "NL-spezifische Subsidenzanalyse"),
]


def generate_report_pdf(report: Report) -> bytes:
    """Generate PDF bytes from report and report_data."""
    try:
        from weasyprint import HTML
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "WeasyPrint runtime dependencies are missing. "
            "Install system libraries for Cairo/Pango/GObject on this host."
        ) from exc

    data = report.report_data or {}
    modules = set(data.get("selected_modules", ["classic"]))
    analysis = data.get("analysis", {})
    points = data.get("raw_points", [])
    histogram = data.get("velocity_histogram", {})

    ampel_value = report.ampel.value if report.ampel else "gruen"
    ampel_label = ampel_value.upper()
    point_count = int(analysis.get("point_count") or len(points))
    has_no_data = point_count == 0
    max_velocity = _safe_float(analysis.get("max_abs_velocity_mm_yr"))
    weighted_velocity = _safe_float(analysis.get("weighted_velocity_mm_yr"))
    max_velocity_label = "—" if has_no_data else f"{max_velocity:.2f}"
    weighted_velocity_label = "—" if has_no_data else f"{weighted_velocity:.2f}"
    geo_score_label = "k. A." if report.geo_score is None else str(report.geo_score)
    summary = escape(str(analysis.get("summary", "")))
    address = escape(report.address_input)
    created_at_str = report.created_at.strftime("%d.%m.%Y %H:%M UTC")
    attribution = escape(
        str(
            analysis.get(
                "attribution",
                "Generated using European Union's Copernicus Land Monitoring Service information",
            )
        )
    )

    aktenzeichen_html = ""
    if report.aktenzeichen:
        aktenzeichen_html = f"<p><strong>Aktenzeichen:</strong> {escape(report.aktenzeichen)}</p>"

    # ── Module-dependent sections ──

    # classic: KPI grid + summary (always rendered since classic is mandatory)
    kpi_html = ""
    if "classic" in modules:
        kpi_html = f"""
        <h2>Ergebnis</h2>
        <span class="ampel ampel-{ampel_value}">{ampel_label}</span>

        <table class="kpi-grid">
            <tr>
                <td>
                    <div class="kpi-value">{point_count}</div>
                    <div class="kpi-label">Messpunkte</div>
                </td>
                <td>
                    <div class="kpi-value">{max_velocity_label}</div>
                    <div class="kpi-label">Max. Geschwindigkeit (mm/a)</div>
                </td>
                <td>
                    <div class="kpi-value">{weighted_velocity_label}</div>
                    <div class="kpi-label">Gewichtet (mm/a)</div>
                </td>
                <td>
                    <div class="kpi-value">{geo_score_label}</div>
                    <div class="kpi-label">GeoScore</div>
                </td>
            </tr>
        </table>

        <h3>Zusammenfassung</h3>
        <p>{summary}</p>
        """

    # timeseries: velocity histogram
    histogram_html = ""
    if "timeseries" in modules and histogram:
        max_count = max(histogram.values()) if histogram.values() else 1
        bars = ""
        for bin_label, count in histogram.items():
            bar_pct = round((count / max_count) * 100) if max_count else 0
            bars += f"""
            <tr>
                <td style="text-align:left; width:60px; font-size:9pt;">{escape(str(bin_label))}</td>
                <td style="padding:4px 8px;">
                    <div style="background:#22C55E; height:18px; width:{bar_pct}%; min-width:2px;"></div>
                </td>
                <td style="text-align:right; width:40px; font-size:9pt;">{count}</td>
            </tr>
            """
        histogram_html = f"""
        <h3>Velocity-Histogramm (mm/a)</h3>
        <table style="border:none; margin-top:8px;">
            {bars}
        </table>
        """
    elif "timeseries" in modules:
        histogram_html = """
        <h3>Velocity-Histogramm</h3>
        <p style="color:#666; font-style:italic;">Keine Messdaten im Untersuchungsradius verfügbar.</p>
        """

    # rawdata: measurement point table
    rawdata_html = ""
    if "rawdata" in modules and points:
        rows = "".join(
            f"""
            <tr>
                <td>{idx + 1}</td>
                <td>{_safe_float(point.get("lat")):.6f}</td>
                <td>{_safe_float(point.get("lon")):.6f}</td>
                <td>{_safe_float(point.get("velocity_mm_yr")):.2f}</td>
                <td>{_safe_float(point.get("distance_m")):.0f}</td>
                <td>{_safe_float(point.get("coherence")):.2f}</td>
            </tr>
            """
            for idx, point in enumerate(points[:30])
        )
        rawdata_html = f"""
        <h3>Messpunkte ({min(len(points), 30)} von {point_count})</h3>
        <table>
            <tr>
                <th>Nr.</th>
                <th>Breitengrad</th>
                <th>Längengrad</th>
                <th>Geschwindigkeit (mm/a)</th>
                <th>Entfernung (m)</th>
                <th>Kohärenz</th>
            </tr>
            {rows}
        </table>
        """
    elif "rawdata" in modules:
        rawdata_html = """
        <h3>Messpunkte</h3>
        <p style="color:#666; font-style:italic;">Keine Messpunkte im Untersuchungsradius gefunden.</p>
        """

    # compliance: full disclaimer + data sources checklist + attribution
    compliance_html = ""
    if "compliance" in modules:
        source_rows = ""
        for status, name, desc in _DATA_SOURCES:
            marker = "✓" if status == "aktiv" else "○"
            color = "#22C55E" if status == "aktiv" else "#999"
            source_rows += f"""
            <tr>
                <td style="text-align:center; color:{color}; font-size:12pt; width:30px;">{marker}</td>
                <td style="text-align:left;"><strong>{escape(name)}</strong></td>
                <td style="text-align:left; color:#666;">{escape(desc)}</td>
            </tr>
            """
        compliance_html = f"""
        <div class="compliance-section">
            <h3>Hinweis</h3>
            <p>Diese Standortauskunft ist ein automatisiertes Datenscreening auf Basis
            von InSAR-Satellitendaten und ersetzt keine Ortsbesichtigung oder
            fachliche Einzelfallbewertung durch einen zugelassenen Sachverständigen.</p>

            <h3>Geprüfte Datenquellen</h3>
            <table style="font-size:9pt;">
                {source_rows}
            </table>

            <p style="margin-top:12px;">{attribution}</p>
        </div>
        """

    # ── Modules listed in PDF ──
    modules_label = ", ".join(sorted(modules))

    # ── Assemble full HTML ──
    html_content = f"""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{ size: A4; margin: 2cm; }}
            body {{
                font-family: Arial, sans-serif;
                font-size: 11pt;
                color: #1a1a1a;
                line-height: 1.5;
            }}
            .header {{
                border-bottom: 3px solid #22C55E;
                padding-bottom: 16px;
                margin-bottom: 24px;
            }}
            h1 {{ margin: 0; font-size: 24pt; letter-spacing: 1px; }}
            .subtitle {{ color: #666; font-size: 10pt; margin-top: 4px; }}
            .ampel {{
                display: inline-block;
                padding: 8px 18px;
                color: white;
                border-radius: 4px;
                font-weight: bold;
                margin-bottom: 12px;
            }}
            .ampel-gruen {{ background: #22C55E; }}
            .ampel-gelb {{ background: #EAB308; color: #1a1a1a; }}
            .ampel-rot {{ background: #EF4444; }}
            .kpi-grid {{
                width: 100%;
                border-collapse: collapse;
                margin: 14px 0 20px 0;
            }}
            .kpi-grid td {{
                border: 1px solid #ddd;
                padding: 10px;
                text-align: center;
            }}
            .kpi-value {{ font-size: 16pt; font-weight: bold; }}
            .kpi-label {{ font-size: 8pt; color: #666; text-transform: uppercase; }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
                font-size: 9pt;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 6px 8px;
                text-align: right;
            }}
            th {{
                background: #f5f5f5;
                text-align: center;
            }}
            .compliance-section {{
                margin-top: 24px;
                border-top: 1px solid #ddd;
                padding-top: 12px;
            }}
            .footer {{
                margin-top: 24px;
                border-top: 1px solid #ddd;
                padding-top: 8px;
                font-size: 8pt;
                color: #999;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>GeoForensic</h1>
            <div class="subtitle">Bodenbewegungsscreening – Standortauskunft</div>
        </div>

        <p><strong>Adresse:</strong> {address}</p>
        <p><strong>Koordinaten:</strong> {report.latitude:.6f}, {report.longitude:.6f}</p>
        <p><strong>Untersuchungsradius:</strong> {report.radius_m} m</p>
        <p><strong>Erstellt:</strong> {created_at_str}</p>
        <p><strong>Module:</strong> {escape(modules_label)}</p>
        {aktenzeichen_html}

        {kpi_html}
        {histogram_html}
        {rawdata_html}
        {compliance_html}

        <div class="footer">
            <p>&copy; GeoForensic {report.created_at.year} — Automatisiertes Screening, keine Gutachterleistung.</p>
        </div>
    </body>
    </html>
    """

    return HTML(string=html_content).write_pdf()
