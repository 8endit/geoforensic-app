"""Generate professional Bodenbericht as HTML (for Chrome Headless → PDF).

Design inspired by the old geoforensic-karte reports + Avista structure.
Calm, professional color palette. Inter font. Card-based layout.
"""

from datetime import datetime, timezone
from html import escape


def _svg_gauge(score: int, size: int = 120) -> str:
    """SVG half-circle gauge for GeoScore."""
    cx, cy, r = size // 2, size // 2 + 10, size // 2 - 12
    circumference = 3.14159 * r  # half circle
    pct = min(max(score / 100, 0), 1)
    offset = circumference * (1 - pct)
    color = "#5B9A6F" if score >= 70 else "#C4A94D" if score >= 40 else "#B85450"
    return f"""<svg width="{size}" height="{size // 2 + 25}" viewBox="0 0 {size} {size // 2 + 25}">
      <path d="M {cx - r} {cy} A {r} {r} 0 0 1 {cx + r} {cy}" fill="none" stroke="#e5e7eb" stroke-width="10" stroke-linecap="round"/>
      <path d="M {cx - r} {cy} A {r} {r} 0 0 1 {cx + r} {cy}" fill="none" stroke="{color}" stroke-width="10" stroke-linecap="round"
        stroke-dasharray="{circumference}" stroke-dashoffset="{offset}"/>
      <text x="{cx}" y="{cy - 8}" text-anchor="middle" font-size="28" font-weight="700" fill="#1e293b">{score}</text>
      <text x="{cx}" y="{cy + 10}" text-anchor="middle" font-size="9" fill="#64748b">von 100</text>
    </svg>"""


def _svg_metal_bars(metals: dict, thresholds: dict) -> str:
    """SVG horizontal bar chart for metals vs. thresholds."""
    if not metals:
        return ""
    names = {"Cd": "Cadmium", "Pb": "Blei", "Hg": "Quecksilber", "As": "Arsen", "Cr": "Chrom", "Cu": "Kupfer", "Ni": "Nickel", "Zn": "Zink"}
    bars = ""
    y = 0
    bar_h = 22
    max_val = max(max(metals.values()), max(thresholds.get(k, 0) for k in metals)) * 1.15
    for sym in ["Cd", "Pb", "Hg", "As", "Cr", "Cu", "Ni", "Zn"]:
        val = metals.get(sym)
        if val is None:
            continue
        thresh = thresholds.get(sym, 999)
        w_val = (val / max_val) * 320
        w_thresh = (thresh / max_val) * 320
        color = "#5B9A6F" if val < thresh else "#C4A94D" if val < thresh * 1.5 else "#B85450"
        bars += f"""
          <g transform="translate(0,{y})">
            <text x="55" y="15" text-anchor="end" font-size="10" font-weight="600" fill="#1e293b">{sym}</text>
            <rect x="62" y="3" width="{w_thresh}" height="{bar_h - 6}" rx="3" fill="#e5e7eb" opacity="0.5"/>
            <rect x="62" y="3" width="{w_val}" height="{bar_h - 6}" rx="3" fill="{color}" opacity="0.85"/>
            <text x="{62 + w_val + 5}" y="15" font-size="9" fill="#64748b">{val:.1f}</text>
          </g>"""
        y += bar_h
    return f"""<svg width="440" height="{y + 20}" style="margin-top:10px;">
      <text x="62" y="{y + 12}" font-size="8" fill="#94a3b8">Grau = BBodSchV Vorsorgewert</text>
      {bars}
    </svg>"""


def _svg_soil_bars(soilgrids: dict) -> str:
    """SVG indicator bars for pH, SOC, bulk density with reference ranges."""
    props = [
        ("phh2o", "pH-Wert", 3, 9, 5.5, 7.5),
        ("soc", "Org. Kohlenstoff", 0, 100, 20, 80),
        ("bdod", "Lagerungsdichte", 0.5, 2.0, 0.8, 1.5),
    ]
    bars = ""
    y = 0
    bar_h = 36
    w = 280
    for key, label, vmin, vmax, gmin, gmax in props:
        val = soilgrids.get(key)
        if val is None:
            continue
        # Positions
        total = vmax - vmin
        x_good_start = ((gmin - vmin) / total) * w
        x_good_w = ((gmax - gmin) / total) * w
        x_val = ((val - vmin) / total) * w
        color = "#5B9A6F" if gmin <= val <= gmax else "#C4A94D"
        bars += f"""
          <g transform="translate(0,{y})">
            <text x="0" y="12" font-size="10" font-weight="600" fill="#1e293b">{label}</text>
            <rect x="110" y="2" width="{w}" height="14" rx="7" fill="#f1f5f9"/>
            <rect x="{110 + x_good_start}" y="2" width="{x_good_w}" height="14" rx="7" fill="{color}" opacity="0.15"/>
            <circle cx="{110 + x_val}" cy="9" r="7" fill="{color}" stroke="white" stroke-width="2"/>
            <text x="{110 + x_val}" y="28" text-anchor="middle" font-size="9" font-weight="600" fill="#1e293b">{val:.1f}</text>
            <text x="110" y="28" font-size="8" fill="#94a3b8">{vmin}</text>
            <text x="{110 + w}" y="28" text-anchor="end" font-size="8" fill="#94a3b8">{vmax}</text>
          </g>"""
        y += bar_h
    if not bars:
        return ""
    return f'<svg width="400" height="{y}" style="margin-top:10px;">{bars}</svg>'


def _svg_texture_donut(clay: float, sand: float, silt: float) -> str:
    """SVG donut chart for soil texture."""
    total = clay + sand + silt
    if total == 0:
        return ""
    cx, cy, r = 55, 55, 40
    circumference = 2 * 3.14159 * r
    segments = [
        (clay / total, "#8B6F47", f"Ton {clay:.0f}%"),
        (sand / total, "#D4C5A9", f"Sand {sand:.0f}%"),
        (silt / total, "#A89B80", f"Schluff {silt:.0f}%"),
    ]
    arcs = ""
    offset = 0
    for pct, color, label in segments:
        dash = pct * circumference
        arcs += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="18" stroke-dasharray="{dash} {circumference - dash}" stroke-dashoffset="{-offset}" transform="rotate(-90 {cx} {cy})"/>'
        offset += dash
    legend = ""
    ly = 20
    for _, color, label in segments:
        legend += f'<rect x="125" y="{ly}" width="10" height="10" rx="2" fill="{color}"/><text x="140" y="{ly + 9}" font-size="10" fill="#1e293b">{label}</text>'
        ly += 18
    return f'<svg width="240" height="110" style="margin-top:8px;">{arcs}{legend}</svg>'


def _status_class(status: str) -> str:
    return {"ok": "ok", "warn": "warn", "critical": "alert"}.get(status, "info")


def _status_label(status: str) -> str:
    return {"ok": "Unbedenklich", "warn": "Erhöht", "critical": "Kritisch"}.get(status, "–")


def _ampel_class(ampel: str) -> str:
    return {"gruen": "healthy", "gelb": "degraded", "rot": "unhealthy"}.get(ampel, "degraded")


def _ampel_label(ampel: str) -> str:
    return {"gruen": "Unauffällig", "gelb": "Auffällig", "rot": "Kritisch"}.get(ampel, "Keine Daten")


def _texture_name(clay: float, sand: float, silt: float) -> str:
    if sand > 65:
        return "Sandboden (leicht, durchlässig)"
    if clay > 40:
        return "Tonboden (schwer, wasserrückhaltend)"
    if silt > 60:
        return "Schluffboden (erosionsanfällig)"
    if 20 <= clay <= 35 and 20 <= sand <= 50:
        return "Lehmboden (ideal, ausgewogen)"
    return "Mischboden"


def _assess_ph(val: float) -> str:
    if 5.5 <= val <= 7.5: return "ok"
    return "warn" if 4.5 <= val <= 8.5 else "critical"

def _assess_soc(val: float) -> str:
    if val >= 20: return "ok"
    return "warn" if val >= 10 else "critical"

def _assess_bdod(val: float) -> str:
    if val < 1.5: return "ok"
    return "warn" if val < 1.7 else "critical"


# BBodSchV thresholds
_THRESHOLDS = {"Cd": 1.0, "Pb": 70.0, "Hg": 0.5, "As": 20.0, "Cr": 60.0, "Cu": 40.0, "Ni": 50.0, "Zn": 150.0}
_METAL_NAMES = {"Cd": "Cadmium", "Pb": "Blei", "Hg": "Quecksilber", "As": "Arsen", "Cr": "Chrom", "Cu": "Kupfer", "Ni": "Nickel", "Zn": "Zink"}

# Quiz text
_NUTZUNG = {
    "Eigenheim / Garten": "Als Eigenheimbesitzer ist die Stabilität Ihres Bodens besonders wichtig für den Werterhalt Ihrer Immobilie und die Sicherheit Ihrer Familie.",
    "Landwirtschaft": "Für landwirtschaftliche Nutzung ist Bodenqualität und -stabilität entscheidend für Ertragssicherheit.",
    "Ich plane einen Hauskauf": "Vor einem Grundstückskauf ist ein Bodenscreening besonders wichtig: Versteckte Bodenprobleme können zu erheblichen Kosten führen, die im Kaufpreis nicht berücksichtigt sind.",
    "Gewerblich": "Bei gewerblicher Nutzung sind Bodenstabilität und mögliche Altlasten relevant für Genehmigungen und Versicherungen.",
}
_DRINGLICHKEIT = {
    "Sofort – es eilt": "Bei erhöhten Werten empfehlen wir eine zeitnahe Begutachtung durch einen Sachverständigen. Wir vermitteln Ihnen gerne einen zertifizierten Experten in Ihrer Region.",
    "Innerhalb der nächsten 2 Wochen": "Planen Sie bei auffälligen Werten eine weiterführende Untersuchung innerhalb der nächsten Wochen ein.",
    "Ich informiere mich nur": "Beobachten Sie die Entwicklung. Wir empfehlen eine erneute Prüfung in 6–12 Monaten.",
}


def generate_html_report(
    address: str,
    lat: float,
    lon: float,
    ampel: str,
    point_count: int,
    mean_velocity: float,
    max_velocity: float,
    geo_score: int | None,
    soil_profile: dict,
    answers: dict | None = None,
) -> str:
    """Generate a professional HTML report string."""
    answers = answers or {}
    now = datetime.now(timezone.utc)
    has_egms = point_count > 0
    soilgrids = soil_profile.get("soilgrids", {})
    metals = soil_profile.get("metals", {})
    metal_status = soil_profile.get("metal_status", {})
    nutrients = soil_profile.get("nutrients", {})
    lucas_dist = soil_profile.get("lucas_distance_km", -1)

    # Overall score
    score = geo_score if geo_score is not None else 50
    score_class = "healthy" if score >= 70 else "degraded" if score >= 40 else "unhealthy"
    score_label = "Gut" if score >= 70 else "Auffällig" if score >= 40 else "Kritisch"

    # Pre-render SVG charts
    gauge_svg = _svg_gauge(score)
    metals_bars_svg = _svg_metal_bars(metals, _THRESHOLDS)
    soil_bars_svg = _svg_soil_bars(soilgrids)
    clay = soilgrids.get("clay")
    sand_v = soilgrids.get("sand")
    silt_v = soilgrids.get("silt")
    texture_donut_svg = _svg_texture_donut(clay, sand_v, silt_v) if clay and sand_v and silt_v else ""

    # Metals rows — only show if LUCAS data is within 50km
    metals_html = ""
    any_metals_warn = False
    metals_too_far = lucas_dist > 50
    if not metals_too_far:
        for sym in ["Cd", "Pb", "Hg", "As", "Cr", "Cu", "Ni", "Zn"]:
            ms = metal_status.get(sym, {})
            val = ms.get("value", metals.get(sym))
            thresh = ms.get("threshold", _THRESHOLDS.get(sym))
            status = ms.get("status", "ok")
            if status in ("warn", "critical"):
                any_metals_warn = True
            if val is not None:
                metals_html += f"""
                <tr>
                  <td><strong>{_METAL_NAMES.get(sym, sym)}</strong> ({sym})</td>
                  <td class="val">{val:.2f} <span class="unit">mg/kg</span></td>
                  <td>{thresh} <span class="unit">mg/kg</span></td>
                  <td><span class="status {_status_class(status)}"><span class="dot {_status_class(status)}"></span> {_status_label(status)}</span></td>
                  <td><span class="source-tag">LUCAS</span></td>
                </tr>"""

    # SoilGrids rows
    sg_rows = ""
    sg_props = [
        ("phh2o", "pH-Wert", "pH", _assess_ph),
        ("soc", "Org. Kohlenstoff (SOC)", "g/kg", _assess_soc),
        ("bdod", "Lagerungsdichte", "g/cm³", _assess_bdod),
        ("clay", "Tongehalt", "%", lambda v: "ok"),
        ("sand", "Sandgehalt", "%", lambda v: "ok"),
        ("silt", "Schluffgehalt", "%", lambda v: "ok"),
    ]
    has_soilgrids = False
    for key, label, unit, assess_fn in sg_props:
        val = soilgrids.get(key)
        if val is not None:
            has_soilgrids = True
            status = assess_fn(val)
            sg_rows += f"""
            <tr>
              <td><strong>{label}</strong></td>
              <td class="val">{val:.1f} <span class="unit">{unit}</span></td>
              <td><span class="status {_status_class(status)}"><span class="dot {_status_class(status)}"></span> {_status_label(status)}</span></td>
              <td><span class="source-tag">SoilGrids 250m</span></td>
            </tr>"""

    # Texture
    clay = soilgrids.get("clay")
    sand = soilgrids.get("sand")
    silt = soilgrids.get("silt")
    texture_html = ""
    if clay is not None and sand is not None and silt is not None:
        texture = _texture_name(clay, sand, silt)
        texture_html = f"""
        <div style="margin-top:12px; padding:12px 16px; background:#f0fdf4; border-radius:8px; border:1px solid #bbf7d0;">
          <strong>Bodenart:</strong> {texture} (Ton {clay:.0f}% · Sand {sand:.0f}% · Schluff {silt:.0f}%)
        </div>"""

    # Nutrients
    nutrients_html = ""
    p_val = nutrients.get("P")
    n_val = nutrients.get("N_total")
    if p_val is not None:
        p_status = "ok" if 30 <= p_val <= 80 else ("warn" if p_val > 80 else "warn")
        nutrients_html += f"""
        <tr>
          <td><strong>Phosphor (P)</strong></td>
          <td class="val">{p_val:.1f} <span class="unit">mg/kg</span></td>
          <td>30–80 <span class="unit">mg/kg</span></td>
          <td><span class="status {_status_class(p_status)}"><span class="dot {_status_class(p_status)}"></span> {'Optimal' if 30 <= p_val <= 80 else 'Erhöht' if p_val > 80 else 'Niedrig'}</span></td>
          <td><span class="source-tag">LUCAS</span></td>
        </tr>"""
    if n_val is not None:
        nutrients_html += f"""
        <tr>
          <td><strong>Gesamtstickstoff (N)</strong></td>
          <td class="val">{n_val:.0f} <span class="unit">mg/kg</span></td>
          <td>–</td>
          <td><span class="status info">Referenzwert</span></td>
          <td><span class="source-tag">LUCAS</span></td>
        </tr>"""

    # Quiz section
    quiz_html = ""
    nutzung = answers.get("nutzung", "")
    dringlichkeit = answers.get("dringlichkeit", "")
    if nutzung or dringlichkeit:
        quiz_parts = ""
        if nutzung in _NUTZUNG:
            quiz_parts += f"<p>{_NUTZUNG[nutzung]}</p>"
        if dringlichkeit in _DRINGLICHKEIT:
            quiz_parts += f"<p><strong>Handlungsempfehlung:</strong> {_DRINGLICHKEIT[dringlichkeit]}</p>"
        quiz_html = f"""
        <div class="card">
          <h2>Ihre individuelle Einschätzung</h2>
          <div class="ss">{quiz_parts}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>Bodenbericht – {escape(address)}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  :root {{
    --green:#5B9A6F; --yellow:#C4A94D; --red:#B85450; --blue:#4A7FB5;
    --dark:#1e293b; --gray:#64748b; --light:#f8fafc; --border:#e2e8f0; --accent:#1E3352;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Inter',-apple-system,sans-serif; color:var(--dark); line-height:1.6; background:white; font-size:12px; }}
  .rc {{ max-width:900px; margin:0 auto; padding:28px 36px; }}
  .header {{
    background:linear-gradient(135deg,#1E3352,#0F2040); color:white;
    padding:32px 36px; border-radius:10px; margin-bottom:20px;
  }}
  .header h1 {{ font-size:22px; font-weight:700; letter-spacing:0.5px; }}
  .header .sub {{ font-size:12px; opacity:.75; margin-bottom:14px; }}
  .header .meta {{ font-size:11px; opacity:.8; display:flex; gap:20px; flex-wrap:wrap; }}
  .card {{
    background:white; border:1px solid var(--border); border-radius:8px;
    padding:20px 24px; margin-bottom:14px; page-break-inside:avoid;
  }}
  .card h2 {{
    font-size:14px; font-weight:600; margin-bottom:14px; padding-bottom:8px;
    border-bottom:2px solid var(--border); display:flex; align-items:center; gap:8px;
    color:var(--accent);
  }}
  .card h3 {{ font-size:12px; font-weight:600; margin:16px 0 8px; color:var(--accent); }}
  .score-overview {{ display:grid; grid-template-columns:120px 1fr; gap:24px; align-items:center; }}
  .score-circle {{
    width:110px; height:110px; border-radius:50%;
    display:flex; flex-direction:column; align-items:center; justify-content:center; margin:0 auto;
  }}
  .score-circle.healthy {{ background:linear-gradient(135deg,#e8f5ec,#d4edda); border:3px solid var(--green); }}
  .score-circle.degraded {{ background:linear-gradient(135deg,#fdf6e3,#fcefc7); border:3px solid var(--yellow); }}
  .score-circle.unhealthy {{ background:linear-gradient(135deg,#fce8e6,#f8d7da); border:3px solid var(--red); }}
  .score-val {{ font-size:32px; font-weight:700; line-height:1; }}
  .score-lbl {{ font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:.05em; margin-top:2px; }}
  .healthy .score-val {{ color:#3d7a50; }} .healthy .score-lbl {{ color:#5B9A6F; }}
  .degraded .score-val {{ color:#8a7a2e; }} .degraded .score-lbl {{ color:#C4A94D; }}
  .unhealthy .score-val {{ color:#943b38; }} .unhealthy .score-lbl {{ color:#B85450; }}
  .ss p {{ font-size:12px; color:var(--gray); margin-bottom:6px; }}
  .ss strong {{ color:var(--dark); }}
  table {{ width:100%; border-collapse:collapse; font-size:11px; }}
  th {{
    text-align:left; padding:7px 9px; background:#f8fafc; font-weight:600;
    color:var(--gray); font-size:9px; text-transform:uppercase; letter-spacing:.04em;
    border-bottom:2px solid var(--border);
  }}
  td {{ padding:7px 9px; border-bottom:1px solid var(--border); vertical-align:top; }}
  tr:last-child td {{ border-bottom:none; }}
  .val {{ font-weight:600; font-variant-numeric:tabular-nums; }}
  .unit {{ color:var(--gray); font-size:9px; }}
  .source-tag {{
    font-size:8px; background:#f1f5f9; color:var(--gray);
    padding:2px 5px; border-radius:3px; white-space:nowrap;
  }}
  .status {{
    display:inline-flex; align-items:center; gap:4px;
    padding:2px 7px; border-radius:12px; font-size:10px; font-weight:600;
  }}
  .status.ok {{ background:#e8f5ec; color:#3d7a50; }}
  .status.warn {{ background:#fdf6e3; color:#8a7a2e; }}
  .status.alert {{ background:#fce8e6; color:#943b38; }}
  .status.info {{ background:#e8f0fe; color:#3b6ab5; }}
  .dot {{ width:6px; height:6px; border-radius:50%; display:inline-block; }}
  .dot.ok {{ background:var(--green); }}
  .dot.warn {{ background:var(--yellow); }}
  .dot.alert {{ background:var(--red); }}
  .dot.info {{ background:var(--blue); }}
  .kpi-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin:12px 0; }}
  .kpi {{ text-align:center; padding:12px 8px; background:#f8fafc; border-radius:8px; border:1px solid var(--border); }}
  .kpi .num {{ font-size:20px; font-weight:700; color:var(--accent); }}
  .kpi .lbl {{ font-size:9px; color:var(--gray); text-transform:uppercase; letter-spacing:.03em; margin-top:2px; }}
  .ampel-badge {{
    display:inline-block; padding:6px 18px; border-radius:6px;
    color:white; font-weight:700; font-size:13px; letter-spacing:.5px;
  }}
  .ampel-badge.healthy {{ background:var(--green); }}
  .ampel-badge.degraded {{ background:var(--yellow); color:#5a4a1a; }}
  .ampel-badge.unhealthy {{ background:var(--red); }}
  .disclaimer {{
    background:#fefce8; border:1px solid #fde68a; border-radius:6px;
    padding:12px 16px; font-size:10px; color:#78600e; margin-top:10px;
  }}
  .two-col {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
  .footer {{
    text-align:center; padding:20px; color:var(--gray); font-size:10px; margin-top:8px;
  }}
  .footer .brand {{ font-size:14px; font-weight:700; color:var(--accent); margin-bottom:2px; }}
  @media print {{
    body {{ background:white; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
    .card {{ break-inside:avoid; }}
  }}
</style>
</head>
<body>
<div class="rc">

<div class="header">
  <h1>Bodenbericht</h1>
  <div class="sub">Umfassende Standort-Risikoeinschätzung</div>
  <div class="meta">
    <span>Erstellt: {now.strftime('%d. %B %Y, %H:%M')} UTC</span>
    <span>{lat:.5f}° N, {lon:.5f}° E</span>
  </div>
</div>

<div style="background:linear-gradient(135deg,#1a3550,#0f2744); color:white; padding:20px 28px; border-radius:8px; margin-bottom:14px;">
  <h2 style="font-size:18px; font-weight:700; border:none; padding:0; margin:0 0 2px; color:white;">{escape(address)}</h2>
  <div style="font-size:11px; opacity:.7; font-family:monospace;">{lat:.5f}° N, {lon:.5f}° E</div>
</div>

<!-- Gesamtbewertung -->
<div class="card">
  <h2>Gesamtbewertung</h2>
  <div class="score-overview">
    <div style="text-align:center;">
      {gauge_svg}
      <div style="font-size:10px; font-weight:600; color:var(--accent); margin-top:-4px;">{score_label}</div>
    </div>
    <div class="ss">
      <p><strong>{'Der Standort zeigt keine kritischen Auffälligkeiten.' if score >= 70 else 'Einzelne Parameter erfordern Aufmerksamkeit.' if score >= 40 else 'Mehrere Parameter zeigen kritische Werte.'}</strong></p>
      <p>{point_count} InSAR-Messpunkte ausgewertet{f', {len(metals)} Schwermetalle geprüft' if metals else ''}{f', Bodenqualität aus SoilGrids 250m' if has_soilgrids else ''}.</p>
    </div>
  </div>
</div>

<!-- Bodenbewegung -->
<div class="card">
  <h2><span class="dot {'ok' if ampel == 'gruen' else 'warn' if ampel == 'gelb' else 'alert'}" style="width:9px;height:9px;"></span> Bodenbewegung (InSAR-Satellitendaten)</h2>
  <div class="kpi-grid">
    <div class="kpi"><div class="num">{point_count}</div><div class="lbl">Messpunkte</div></div>
    <div class="kpi"><div class="num">{f'{mean_velocity:.1f}' if has_egms else '–'}</div><div class="lbl">Mittl. Geschw. (mm/a)</div></div>
    <div class="kpi"><div class="num">{f'{max_velocity:.1f}' if has_egms else '–'}</div><div class="lbl">Max. Geschw. (mm/a)</div></div>
    <div class="kpi"><div class="num">{geo_score if geo_score else '–'}</div><div class="lbl">GeoScore</div></div>
  </div>
  <p style="font-size:12px; color:var(--gray);">
    <span class="ampel-badge {_ampel_class(ampel)}">{_ampel_label(ampel)}</span>
    &nbsp; {'Keine auffälligen Bodenbewegungen im Untersuchungsradius. Stabile Lage.' if ampel == 'gruen' else 'Vereinzelt erhöhte Bodenbewegungen gemessen. Weitere Beobachtung empfohlen.' if ampel == 'gelb' else 'Kritische Bodenbewegungen gemessen. Fachliche Einschätzung dringend empfohlen.' if has_egms else 'Für diesen Standort liegen keine InSAR-Satellitendaten vor.'}
  </p>
</div>

<!-- Schwermetalle -->
{'<div class="card"><h2><span class="dot info" style="width:9px;height:9px;"></span> Schwermetall-Analyse</h2><div class="disclaimer" style="background:#e8f0fe; border-color:#93b4e0; color:#2c5282;"><strong>Hinweis:</strong> Für diesen Standort liegen keine regionalen Bodenproben vor (nächster LUCAS-Messpunkt: ' + f'{lucas_dist:.0f}' + ' km). Eine zuverlässige Schwermetall-Einschätzung ist aus der Ferne nicht möglich. Wir empfehlen eine lokale Bodenprobe.</div></div>' if metals_too_far and metals else '<div class="card"><h2><span class="dot ' + ("warn" if any_metals_warn else "ok") + '" style="width:9px;height:9px;"></span> Schwermetall-Analyse</h2>' + f'<p style="font-size:10px; color:var(--gray); margin-bottom:10px;">Basierend auf LUCAS Topsoil-Daten (nächster Messpunkt: {lucas_dist:.1f} km) · Vergleich: BBodSchV Vorsorgewerte</p><table><thead><tr><th>Stoff</th><th>Messwert</th><th>Vorsorgewert</th><th>Status</th><th>Quelle</th></tr></thead><tbody>{metals_html}</tbody></table>{metals_bars_svg}</div>' if metals and not metals_too_far else ''}

<!-- Bodenqualität -->
{'<div class="card"><h2><span class="dot ok" style="width:9px;height:9px;"></span> Bodenqualität</h2><table><thead><tr><th>Eigenschaft</th><th>Wert</th><th>Bewertung</th><th>Quelle</th></tr></thead><tbody>' + sg_rows + '</tbody></table>' + soil_bars_svg + '<div style="display:flex; align-items:center; gap:20px; margin-top:12px;">' + texture_donut_svg + texture_html + '</div></div>' if has_soilgrids else ''}

<!-- Nährstoffe -->
{'<div class="card"><h2>Nährstoffe</h2><table><thead><tr><th>Parameter</th><th>Wert</th><th>Referenz</th><th>Status</th><th>Quelle</th></tr></thead><tbody>' + nutrients_html + '</tbody></table><p style="font-size:9px; color:var(--gray); margin-top:8px;">Quelle: LUCAS Topsoil Survey (nächster Messpunkt: ' + f'{lucas_dist:.1f}' + ' km)</p></div>' if nutrients_html and not metals_too_far else ''}

<!-- Individuelle Einschätzung -->
{quiz_html}

<!-- Datenquellen -->
<div class="card">
  <h2>Geprüfte Datenquellen</h2>
  <div class="two-col">
    <div>
      <h3>Satellitendaten</h3>
      <table>
        <tr><td><span class="source-tag">EGMS</span></td><td>Ground Motion Service (Sentinel-1, 2019–2022)</td></tr>
        <tr><td><span class="source-tag">Nominatim</span></td><td>OpenStreetMap Geocodierung</td></tr>
      </table>
      <h3>Bodendatenbanken</h3>
      <table>
        <tr><td><span class="source-tag">LUCAS</span></td><td>EU Bodenproben — Schwermetalle, Nährstoffe</td></tr>
        <tr><td><span class="source-tag">SoilGrids</span></td><td>ISRIC 250m — pH, SOC, Textur, Dichte</td></tr>
      </table>
    </div>
    <div>
      <h3>Rechtliche Grundlagen</h3>
      <table>
        <tr><td><span class="source-tag">BBodSchV</span></td><td>Vorsorge- und Maßnahmenwerte</td></tr>
        <tr><td><span class="source-tag">(EU) 2025/2360</span></td><td>Soil Monitoring Directive</td></tr>
      </table>
      <h3>In Vorbereitung</h3>
      <table>
        <tr><td><span class="source-tag" style="opacity:.5;">Hochwasser</span></td><td style="color:#aaa;">EU-Hochwasserrichtlinie</td></tr>
        <tr><td><span class="source-tag" style="opacity:.5;">Altlasten</span></td><td style="color:#aaa;">BBodSchG Kataster</td></tr>
      </table>
    </div>
  </div>
</div>

<div class="disclaimer">
  <strong>Hinweis:</strong> Dieser Bodenbericht ist ein automatisiertes Datenscreening auf Basis öffentlich verfügbarer Fernerkundungs- und Bodendaten (Copernicus EGMS, LUCAS, SoilGrids). Er ersetzt keine Ortsbesichtigung, Laboranalyse oder fachliche Einzelfallbewertung durch einen zugelassenen Sachverständigen gem. §9 BBodSchG. Messwerte basieren auf regionalen Durchschnittswerten und nicht auf standortspezifischen Beprobungen.
  <br><br>
  <em>Generated using European Union's Copernicus Land Monitoring Service information.</em>
</div>

<div class="footer">
  <div class="brand">Bodenbericht</div>
  <div>Umfassende Standort-Risikoeinschätzung · bodenbericht.de</div>
  <div style="margin-top:4px;">Erstellt: {now.strftime('%d.%m.%Y %H:%M')} UTC</div>
  <div style="margin-top:2px;opacity:.6;">© {now.year} Bodenbericht</div>
</div>

</div></body></html>"""
