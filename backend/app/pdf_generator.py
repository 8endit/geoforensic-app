"""PDF report generation using WeasyPrint."""

from html import escape

from app.models import Report


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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
    analysis = data.get("analysis", {})
    points = data.get("raw_points", [])
    ampel_value = report.ampel.value if report.ampel else "gruen"
    ampel_label = ampel_value.upper()
    point_count = int(analysis.get("point_count") or len(points))
    max_velocity = _safe_float(analysis.get("max_abs_velocity_mm_yr"))
    weighted_velocity = _safe_float(analysis.get("weighted_velocity_mm_yr"))
    geo_score = report.geo_score or 0
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

    rows_html = "".join(
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

    aktenzeichen_html = ""
    if report.aktenzeichen:
        aktenzeichen_html = f"<p><strong>Aktenzeichen:</strong> {escape(report.aktenzeichen)}</p>"

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
            .disclaimer {{
                margin-top: 24px;
                border-top: 1px solid #ddd;
                padding-top: 12px;
                font-size: 8pt;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>GeoForensic</h1>
            <div class="subtitle">Bodenbewegungsscreening - Standortauskunft</div>
        </div>

        <p><strong>Adresse:</strong> {address}</p>
        <p><strong>Koordinaten:</strong> {report.latitude:.6f}, {report.longitude:.6f}</p>
        <p><strong>Untersuchungsradius:</strong> {report.radius_m} m</p>
        <p><strong>Erstellt:</strong> {created_at_str}</p>
        {aktenzeichen_html}

        <h2>Ergebnis</h2>
        <span class="ampel ampel-{ampel_value}">{ampel_label}</span>

        <table class="kpi-grid">
            <tr>
                <td>
                    <div class="kpi-value">{point_count}</div>
                    <div class="kpi-label">Messpunkte</div>
                </td>
                <td>
                    <div class="kpi-value">{max_velocity:.2f}</div>
                    <div class="kpi-label">Max. Geschwindigkeit (mm/a)</div>
                </td>
                <td>
                    <div class="kpi-value">{weighted_velocity:.2f}</div>
                    <div class="kpi-label">Gewichtet (mm/a)</div>
                </td>
                <td>
                    <div class="kpi-value">{geo_score}</div>
                    <div class="kpi-label">GeoScore</div>
                </td>
            </tr>
        </table>

        <h3>Zusammenfassung</h3>
        <p>{summary}</p>

        <h3>Messpunkte ({min(len(points), 30)} von {point_count})</h3>
        <table>
            <tr>
                <th>Nr.</th>
                <th>Breitengrad</th>
                <th>Laengengrad</th>
                <th>Geschwindigkeit (mm/a)</th>
                <th>Entfernung (m)</th>
                <th>Kohaerenz</th>
            </tr>
            {rows_html}
        </table>

        <div class="disclaimer">
            <p><strong>Hinweis:</strong> Diese Standortauskunft ist ein automatisiertes Datenscreening auf Basis von InSAR-Daten und ersetzt keine Ortsbesichtigung oder fachliche Einzelfallbewertung.</p>
            <p>{attribution}</p>
            <p>&copy; GeoForensic {report.created_at.year}</p>
        </div>
    </body>
    </html>
    """

    return HTML(string=html_content).write_pdf()
