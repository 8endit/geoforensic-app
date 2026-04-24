"""Teaser-Bodenbericht as HTML (for Chrome Headless → PDF).

Free lead-magnet variant shipped by bodenbericht.de. Layout is split into
three zones:

    SICHTBAR  — Gesamt-Ampel + GeoScore, Bodenbewegung (Punkt + Ampel),
                Individuelle Einschaetzung (aus Quiz oder Ampel-Fallback)
    BLURRED   — Schwermetalle, Bodenqualitaet, Naehrstoffe,
                InSAR-Detailwerte. Each rendered with realistic values
                under CSS filter: blur + Lock-Pill. Real data when available,
                mock fallback otherwise.
    CTA       — Vollbericht-Warteliste (Stripe link replaces this when live)

The mock data shown under blur is exactly what `generate_full_report` will
deliver unblurred when the user upgrades. Do not promise sections here that
the full report does not actually render.
"""

import base64
import hashlib
from datetime import datetime, timezone
from html import escape
from pathlib import Path

_HERE = Path(__file__).resolve()
# Logo lives in /app/landing/ inside the docker container (bind-mounted) or in
# <repo>/landing/ for local dev. Try both before giving up.
_LOGO_CANDIDATES = [
    _HERE.parents[1] / "landing" / "images" / "logo-horizontal.png",  # /app/landing in container
    _HERE.parents[2] / "landing" / "images" / "logo-horizontal.png",  # repo root in local dev
]
_LOGO_DATA_URI = ""
for _p in _LOGO_CANDIDATES:
    try:
        _LOGO_DATA_URI = "data:image/png;base64," + base64.b64encode(_p.read_bytes()).decode("ascii")
        break
    except OSError:
        continue


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
    return {"ok": "Unbedenklich", "warn": "Erhöht", "critical": "Kritisch"}.get(status, "?")


def _ampel_class(ampel: str) -> str:
    return {"gruen": "healthy", "gelb": "degraded", "rot": "unhealthy"}.get(ampel, "degraded")


def _ampel_label(ampel: str) -> str:
    return {"gruen": "Unauffällig", "gelb": "Auffällig", "rot": "Kritisch"}.get(ampel, "Keine Daten")


_EINSCHAETZUNG_FALLBACK = {
    "gruen": "Für Standorte im <strong>grünen Bereich</strong> empfehlen wir eine Wiederholung des Screenings in 12 bis 24 Monaten. Akute Maßnahmen sind nach Datenlage nicht erforderlich.",
    "gelb":  "Für Standorte im <strong>gelben Bereich</strong> empfehlen wir eine Wiederholung des Screenings in 6 bis 12 Monaten. Bei einem älteren Fundament oder sichtbaren Rissen lohnt sich eine Begutachtung durch einen Baugrundsachverständigen.",
    "rot":   "Für Standorte im <strong>roten Bereich</strong> empfehlen wir eine zeitnahe Vor-Ort-Begutachtung durch einen nach §18 BBodSchG zugelassenen Sachverständigen. Ansprechpartner ist die untere Bodenschutzbehörde Ihres Landkreises.",
}

_LOCK_PILL_HTML = """<div class="lock-overlay"><span class="lock-pill">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
    <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
  </svg>Im Vollbericht enthalten</span></div>"""


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
    "Sofort, es eilt": "Bei erhöhten Werten empfehlen wir eine zeitnahe Vor-Ort-Begutachtung durch einen nach §18 BBodSchG zugelassenen Sachverständigen. Ansprechpartner für eine Liste ist das Umweltamt Ihres Landkreises oder Ihrer kreisfreien Stadt (die zuständige untere Bodenschutzbehörde nach §11 BBodSchG).",
    "Innerhalb der nächsten 2 Wochen": "Planen Sie bei auffälligen Werten eine weiterführende Untersuchung innerhalb der nächsten Wochen ein.",
    "Ich informiere mich nur": "Beobachten Sie die Entwicklung. Wir empfehlen eine erneute Prüfung in 6 bis 12 Monaten.",
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
    radius_m: int | None = None,
    egms_period_start: int | None = None,
    egms_period_end: int | None = None,
    operator_legal_name: str | None = None,
    operator_imprint_url: str | None = None,
    map_data_uri: str | None = None,
    region: dict | None = None,
) -> str:
    """Generate a professional HTML report string."""
    answers = answers or {}
    now = datetime.now(timezone.utc)
    has_egms = point_count > 0

    # Pull defaults from settings so callers that don't pass these still
    # render a correct report (and we have one source of truth for radius +
    # measurement window instead of hardcoded copy).
    from app.config import get_settings
    _settings = get_settings()
    if radius_m is None:
        radius_m = _settings.egms_radius_m
    if egms_period_start is None:
        egms_period_start = _settings.egms_period_start
    if egms_period_end is None:
        egms_period_end = _settings.egms_period_end
    if operator_legal_name is None:
        operator_legal_name = _settings.operator_legal_name
    if operator_imprint_url is None:
        operator_imprint_url = _settings.operator_imprint_url
    egms_period = f"{egms_period_start}&ndash;{egms_period_end}"

    # Bericht-Nr: "YYYYMMDD-XXXXXXXX" where XXXXXXXX is an 8-char hex hash of
    # date + address. Stable for a given address on a given day (idempotent
    # when a user re-requests the report), but does not reveal any sequential
    # counter (old format "-0042" leaked daily volume).
    _date_str = now.strftime("%Y%m%d")
    _nr_hash = hashlib.sha256(f"{_date_str}|{address}".encode("utf-8")).hexdigest()[:8].upper()
    report_number = f"{_date_str}-{_nr_hash}"

    # Map snippet: if the caller fetched one we embed it; otherwise show a
    # grey coord-labelled fallback so the PDF layout never collapses.
    if map_data_uri:
        map_html = f'<img src="{map_data_uri}" alt="Kartenausschnitt der Adresse" class="map-snippet">'
    else:
        map_html = (
            '<div class="map-fallback">'
            'Karte derzeit nicht verfügbar'
            f'<div class="coords-fallback">{lat:.4f}° N · {lon:.4f}° E</div>'
            '</div>'
        )

    # Region line: Landkreis · Bundesland · Land. Rendered small under the
    # address, only if Nominatim supplied the components. Falls back to empty
    # string so the layout collapses cleanly when nothing is available.
    region_html = ""
    if region:
        region_parts = [p for p in (region.get("county"), region.get("state"), region.get("country")) if p]
        if region_parts:
            region_html = (
                '<div class="region">'
                + escape(" · ".join(region_parts))
                + '</div>'
            )
    soilgrids = soil_profile.get("soilgrids", {})
    metals = soil_profile.get("metals", {})
    metal_status = soil_profile.get("metal_status", {})
    nutrients = soil_profile.get("nutrients", {})
    lucas_dist = soil_profile.get("lucas_distance_km", -1)

    # Overall score
    score = geo_score if geo_score is not None else 50
    score_label = "Gut" if score >= 70 else "Beobachten" if score >= 40 else "Kritisch"

    gauge_svg = _svg_gauge(score)
    bb_dot = "ok" if ampel == "gruen" else "warn" if ampel == "gelb" else "alert"
    bb_text = (
        "Keine auffälligen Bodenbewegungen im Untersuchungsradius. Stabile Lage." if ampel == "gruen"
        else "Vereinzelt erhöhte Bodenbewegungen gemessen. Weitere Beobachtung empfohlen." if ampel == "gelb"
        else "Kritische Bodenbewegungen gemessen. Fachliche Einschätzung empfohlen." if ampel == "rot"
        else "Für diesen Standort liegen keine InSAR-Satellitendaten im Untersuchungsradius vor."
    )

    # Einschaetzung — quiz answers if present, otherwise ampel-specific fallback
    nutzung = answers.get("nutzung", "")
    dringlichkeit = answers.get("dringlichkeit", "")
    if nutzung in _NUTZUNG or dringlichkeit in _DRINGLICHKEIT:
        ein_parts = []
        if nutzung in _NUTZUNG:
            ein_parts.append(f"<p>{_NUTZUNG[nutzung]}</p>")
        if dringlichkeit in _DRINGLICHKEIT:
            ein_parts.append(f"<p><strong>Handlungsempfehlung:</strong> {_DRINGLICHKEIT[dringlichkeit]}</p>")
        einschaetzung_html = "".join(ein_parts)
    else:
        einschaetzung_html = f"<p>{_EINSCHAETZUNG_FALLBACK.get(ampel, _EINSCHAETZUNG_FALLBACK['gelb'])}</p>"

    # The locked cards render opaque placeholders (▓▓▓) instead of real or
    # mock values. This is the paywall hardening from fix-list item 5: even
    # if a reader strips the CSS blur filter, copies PDF text, or runs OCR,
    # only placeholder tokens appear. Real values are reserved for the
    # full report. We keep the per-metal cells structurally so the layout
    # still communicates "eight metals are screened here".
    metal_cells = "".join(
        f'<div class="metal-cell"><div class="metal-sym">{sym}</div><div class="metal-val">▓▓▓ mg/kg</div></div>'
        for sym in ["Cd", "Pb", "Hg", "As", "Cr", "Cu", "Ni", "Zn"]
    )

    logo_html = (
        f'<img src="{_LOGO_DATA_URI}" alt="Bodenbericht" class="brand-logo">'
        if _LOGO_DATA_URI
        else '<span class="brand-text">Bodenbericht</span>'
    )

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>Bodenbericht: {escape(address)}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  :root {{
    --green:#5B9A6F; --yellow:#C4A94D; --red:#B85450;
    --dark:#1e293b; --gray:#64748b; --border:#e2e8f0; --accent:#1E3352; --accent-deep:#0F2040;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Inter',-apple-system,sans-serif; color:var(--dark); line-height:1.55; background:white; font-size:12px; }}
  .rc {{ max-width:900px; margin:0 auto; padding:24px 32px; }}

  .header {{
    background:linear-gradient(135deg,var(--accent),var(--accent-deep));
    color:white; padding:18px 28px; border-radius:10px; margin-bottom:18px;
    display:flex; justify-content:space-between; align-items:center; gap:24px;
    position:relative; overflow:hidden;
  }}
  .header::before {{
    content:""; position:absolute; inset:0;
    background-image:linear-gradient(rgba(255,255,255,.04) 1px, transparent 1px),
                     linear-gradient(90deg, rgba(255,255,255,.04) 1px, transparent 1px);
    background-size:28px 28px;
  }}
  .header > * {{ position:relative; }}
  .brand-logo {{ height:30px; width:auto; filter:brightness(0) invert(1); opacity:.95; }}
  .brand-text {{ font-size:18px; font-weight:700; letter-spacing:.5px; }}
  .header-meta {{ font-size:10px; opacity:.85; text-align:right; }}
  .header-meta .nr {{ font-family:ui-monospace,monospace; }}

  .address-map-row {{
    display:flex; gap:16px; align-items:stretch;
    margin:6px 4px 18px;
  }}
  .address-map-row .address-block {{
    flex:1 1 auto; margin:0;
    padding-right:16px; border-right:1px solid #eef1f3;
  }}
  .map-snippet {{
    width:260px; height:160px; border-radius:6px;
    border:1px solid var(--border); display:block; flex:0 0 auto;
  }}
  .map-fallback {{
    width:260px; height:160px; flex:0 0 auto;
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    border-radius:6px; border:1px dashed #d1d5db; background:#f9fafb;
    color:var(--gray); font-size:10px; text-align:center; padding:0 10px;
  }}
  .map-fallback .coords-fallback {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    color:var(--dark); margin-top:4px; font-size:11px;
  }}
  .address-block {{ margin:6px 4px 18px; }}
  .address-block .label {{
    font-size:10px; text-transform:uppercase; letter-spacing:.08em;
    color:var(--gray); font-weight:600;
  }}
  .address-block .addr {{
    font-size:18px; font-weight:700; color:var(--accent); line-height:1.25; margin-top:2px;
  }}
  .address-block .region {{ font-size:11px; color:var(--dark); margin-top:3px; opacity:0.75; }}
  .address-block .coords {{ font-size:10px; color:var(--gray); margin-top:2px; }}

  .section-label {{
    display:flex; align-items:center; gap:10px;
    font-size:9px; font-weight:700; letter-spacing:.12em;
    text-transform:uppercase; color:var(--gray);
    margin:18px 4px 6px;
  }}
  .section-label::before, .section-label::after {{
    content:""; flex:1; height:1px; background:var(--border);
  }}

  .card {{
    background:white; border:1px solid var(--border); border-radius:8px;
    padding:18px 22px; margin-bottom:12px; page-break-inside:avoid;
    position:relative;
  }}
  .card h2 {{
    font-size:13px; font-weight:600; margin-bottom:12px; padding-bottom:6px;
    border-bottom:1px solid var(--border); color:var(--accent);
    display:flex; align-items:center; gap:8px;
  }}
  .ss p {{ font-size:12px; color:var(--gray); margin-bottom:6px; }}
  .ss strong {{ color:var(--dark); }}

  .gauge-row {{ display:grid; grid-template-columns:130px 1fr; gap:20px; align-items:center; }}
  .gauge-row .label {{ font-size:10px; font-weight:600; color:var(--accent); text-align:center; margin-top:-4px; }}

  .kpi-grid {{ display:grid; grid-template-columns:repeat(2,1fr); gap:10px; margin:8px 0 10px; }}
  .kpi {{ text-align:center; padding:12px 8px; background:#f8fafc; border-radius:8px; border:1px solid var(--border); }}
  .kpi .num {{ font-size:22px; font-weight:700; color:var(--accent); }}
  .kpi .lbl {{ font-size:9px; color:var(--gray); text-transform:uppercase; letter-spacing:.03em; margin-top:2px; }}

  .ampel-badge {{ display:inline-block; padding:5px 14px; border-radius:6px;
    color:white; font-weight:700; font-size:11px; letter-spacing:.5px; }}
  .ampel-badge.healthy {{ background:var(--green); }}
  .ampel-badge.degraded {{ background:var(--yellow); color:#5a4a1a; }}
  .ampel-badge.unhealthy {{ background:var(--red); }}

  .dot {{ width:9px; height:9px; border-radius:50%; display:inline-block; }}
  .dot.ok {{ background:var(--green); }}
  .dot.warn {{ background:var(--yellow); }}
  .dot.alert {{ background:var(--red); }}

  /* Paywall-gated cards */
  .locked {{ overflow:hidden; }}
  .locked .teaser-note {{
    font-size:11px; color:var(--dark); margin:0 0 10px; line-height:1.5;
    padding:6px 10px; background:#f0f5f1; border-left:2px solid var(--accent);
    border-radius:0 4px 4px 0;
  }}
  .locked .locked-content {{
    filter: blur(8px) saturate(.7); pointer-events:none; user-select:none;
    -webkit-filter: blur(8px) saturate(.7);
  }}
  .lock-overlay {{
    position:absolute; inset:0;
    background:repeating-linear-gradient(135deg,
      rgba(30,51,82,.04) 0 8px,
      rgba(30,51,82,.08) 8px 16px);
    display:flex; align-items:center; justify-content:center;
  }}
  .lock-pill {{
    display:inline-flex; align-items:center; gap:6px;
    background:rgba(255,255,255,.96); border:1px solid #cbd5e1;
    border-radius:999px; padding:5px 12px;
    font-size:10px; font-weight:600; color:var(--accent);
    box-shadow:0 4px 10px -4px rgba(12,29,58,.25); letter-spacing:.02em;
  }}
  .lock-pill svg {{ width:11px; height:11px; }}

  .metal-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:6px; }}
  .metal-cell {{ background:#f8fafc; border-radius:5px; padding:8px 4px; text-align:center; }}
  .metal-sym {{ font-weight:700; color:var(--accent); font-size:13px; }}
  .metal-val {{ color:var(--gray); font-size:9px; margin-top:2px; }}

  .stat-grid-3 {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }}
  .stat-cell {{ background:#f8fafc; border-radius:6px; padding:10px 8px; text-align:center; }}
  .stat-cell .lbl {{ font-size:9px; color:var(--gray); text-transform:uppercase; letter-spacing:.03em; }}
  .stat-cell .val {{ font-size:16px; font-weight:700; color:var(--accent); margin-top:2px; }}
  .stat-cell .sub {{ font-size:9px; color:var(--gray); margin-top:1px; }}
  .stat-cell.warn .val {{ color:#8a7a2e; }}

  /* CTA */
  .cta {{
    background:linear-gradient(135deg, var(--accent-deep), var(--accent));
    color:white; border-radius:10px; padding:22px 26px; margin:14px 0 8px;
    text-align:center; position:relative; overflow:hidden;
    page-break-inside:avoid; break-inside:avoid;
  }}
  .cta > * {{ position:relative; }}
  .cta .kicker {{ font-size:10px; text-transform:uppercase; letter-spacing:.1em; color:#a7d4b5; font-weight:700; }}
  .cta h3 {{ font-size:15px; font-weight:700; margin:4px 0 6px; color:white; }}
  .cta p {{ font-size:11px; color:#cbd5e1; max-width:520px; margin:0 auto 12px; }}
  .cta a {{
    display:inline-block; background:var(--green); color:white; text-decoration:none;
    font-weight:700; font-size:12px; padding:10px 20px; border-radius:8px;
  }}
  .cta .small {{ font-size:9px; color:#cbd5e1; opacity:.8; margin-top:8px; }}

  .disclaimer {{
    background:#fefce8; border:1px solid #fde68a; border-radius:6px;
    padding:12px 16px; font-size:10px; color:#78600e; margin-top:10px;
  }}
  .footer {{
    text-align:center; padding:18px; color:var(--gray); font-size:10px; margin-top:6px;
  }}
  .footer .brand {{ font-size:13px; font-weight:700; color:var(--accent); margin-bottom:2px; }}

  @media print {{
    body {{ background:white; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
    .card {{ break-inside:avoid; }}
  }}
</style>
</head>
<body>
<div class="rc">

<div class="header">
  {logo_html}
  <div class="header-meta">
    <div>Bericht-Nr. <span class="nr">{report_number}</span></div>
    <div>Erstellt: {now.strftime('%d.%m.%Y')}</div>
  </div>
</div>

<div class="address-map-row">
  <div class="address-block">
    <div class="label">Gesamtbewertung für</div>
    <div class="addr">{escape(address)}</div>
    {region_html}
    <div class="coords">{lat:.4f}° N · {lon:.4f}° E</div>
  </div>
  {map_html}
</div>

<div class="section-label">Sichtbar im kostenlosen Bericht</div>

<div class="card">
  <h2>Gesamt-Ampel &amp; GeoScore</h2>
  <div class="gauge-row">
    <div>
      {gauge_svg}
      <div class="label">{score_label}</div>
    </div>
    <div class="ss">
      <p><strong>{'Der Standort zeigt keine kritischen Auffälligkeiten.' if score >= 70 else 'Einzelne Parameter erfordern Aufmerksamkeit.' if score >= 40 else 'Mehrere Parameter zeigen kritische Werte.'}</strong></p>
      <p>{point_count} InSAR-Messpunkte im Umkreis von {radius_m}&thinsp;m ausgewertet. Die Ampel basiert auf der mittleren Geschwindigkeit aller Messpunkte; die konkreten mm/a-Werte stehen im Vollbericht.</p>
    </div>
  </div>
  <p class="ss" style="margin-top:10px; padding-top:8px; border-top:1px solid #eef1f3;"><span style="color:var(--gray); font-size:10px;">Der GeoScore kombiniert mittlere Geschwindigkeit, Streuung und Messpunktdichte im Umkreis.</span></p>
</div>

<div class="card">
  <h2><span class="dot {bb_dot}"></span> Bodenbewegung (InSAR-Satellitendaten)</h2>
  <div class="kpi-grid">
    <div class="kpi"><div class="num">{point_count}</div><div class="lbl">Messpunkte im Umkreis von {radius_m}&thinsp;m</div></div>
    <div class="kpi" style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
      <span class="ampel-badge {_ampel_class(ampel)}">{_ampel_label(ampel)}</span>
      <div class="lbl" style="margin-top:6px;">Status Bodenbewegung</div>
    </div>
  </div>
  <p class="ss"><span style="color:var(--gray);">{bb_text}</span></p>
  <p class="ss" style="margin-top:6px;"><span style="color:var(--gray); font-size:10px;">Messzeitraum: {egms_period} (Copernicus EGMS, Sentinel-1).</span></p>
</div>

<div class="card">
  <h2>Ihre individuelle Einschätzung</h2>
  <div class="ss">{einschaetzung_html}</div>
</div>

<div class="section-label">Im Vollbericht enthalten</div>

<div class="card locked">
  <h2>Schwermetalle &amp; Schadstoffe</h2>
  <p class="teaser-note">Im Vollbericht: exakte Messwerte für Cd, Pb, Hg, As, Cr, Cu, Ni und Zn, jeweils mit Ampel-Einordnung gegen die BBodSchV-Vorsorgewerte.</p>
  <div class="locked-content">
    <div class="metal-grid">{metal_cells}</div>
  </div>
  {_LOCK_PILL_HTML}
</div>

<div class="card locked">
  <h2>Bodenqualität &amp; Textur</h2>
  <p class="teaser-note">Im Vollbericht: pH-Wert, organischer Kohlenstoff, Lagerungsdichte und die konkrete Bodenart (Ton/Sand/Schluff-Anteile) aus dem SoilGrids-250&thinsp;m-Raster.</p>
  <div class="locked-content">
    <div class="stat-grid-3">
      <div class="stat-cell"><div class="lbl">pH-Wert</div><div class="val">▓▓▓</div><div class="sub">Säuregrad</div></div>
      <div class="stat-cell"><div class="lbl">Org. Kohlenstoff</div><div class="val">▓▓▓ g/kg</div><div class="sub">Humusgehalt</div></div>
      <div class="stat-cell"><div class="lbl">Bodenart</div><div class="val" style="font-size:13px;">▓▓▓</div><div class="sub">Ton/Sand/Schluff</div></div>
    </div>
  </div>
  {_LOCK_PILL_HTML}
</div>

<div class="card locked">
  <h2>Nährstoffe (Phosphor &amp; Stickstoff)</h2>
  <p class="teaser-note">Im Vollbericht: Phosphor- und Stickstoff-Werte aus der EU-LUCAS-Topsoil-Datenbank, eingeordnet gegen agronomische Referenzbereiche.</p>
  <div class="locked-content">
    <div class="stat-grid-3" style="grid-template-columns:repeat(2,1fr);">
      <div class="stat-cell"><div class="lbl">Phosphor (P)</div><div class="val">▓▓▓ mg/kg</div><div class="sub">Nährstoffgehalt</div></div>
      <div class="stat-cell"><div class="lbl">Gesamt-Stickstoff (N)</div><div class="val">▓▓▓ mg/kg</div><div class="sub">Referenzwert</div></div>
    </div>
  </div>
  {_LOCK_PILL_HTML}
</div>

<div class="card locked">
  <h2>InSAR-Detailwerte der Messpunkte</h2>
  <p class="teaser-note">Im Vollbericht: mittlere und maximale Geschwindigkeit in mm/a, komplette Zeitreihe pro Messpunkt seit 2017 und eine Trendklassifikation (beschleunigend / stabil / abklingend).</p>
  <div class="locked-content">
    <div class="stat-grid-3">
      <div class="stat-cell warn"><div class="lbl">Mittl. Geschw.</div><div class="val">▓▓▓ mm/a</div></div>
      <div class="stat-cell warn"><div class="lbl">Max. Geschw.</div><div class="val">▓▓▓ mm/a</div></div>
      <div class="stat-cell"><div class="lbl">Trend</div><div class="val">▓▓▓</div></div>
    </div>
    <p class="ss" style="margin-top:8px;"><span style="color:var(--gray); font-size:10px;">Messzeitraum {egms_period}, {radius_m}&thinsp;m-Radius (Copernicus EGMS L3 Ortho, Sentinel-1).</span></p>
  </div>
  {_LOCK_PILL_HTML}
</div>

<div class="cta">
  <div class="kicker">Vollbericht</div>
  <h3>Alles sehen, was hier noch verdeckt ist</h3>
  <p>Schwermetalle, Bodenqualität, Nährstoffe und die detaillierten InSAR-Geschwindigkeitswerte erscheinen ungeschwärzt im Vollbericht — inklusive PDF-Download.</p>
  <a href="https://bodenbericht.de/#premium">Auf die Warteliste</a>
  <div class="small">Noch nicht bestellbar. Early-Bird-Platz sichern, Start-Rabatt erhalten.</div>
</div>

<div class="card">
  <h2 style="font-size:10px; text-transform:uppercase; letter-spacing:.05em; color:var(--gray); border:none; padding:0; margin:0 0 6px;">Datenquellen</h2>
  <p style="font-size:11px; color:var(--dark); margin:0;">
    Copernicus EGMS (Sentinel-1) · LUCAS Topsoil Survey (EU) · SoilGrids 250m (ISRIC) · OpenStreetMap Nominatim · Referenzwerte: BBodSchV
  </p>
</div>

<div class="disclaimer">
  <strong>Hinweis:</strong> Dieser Bodenbericht ist ein automatisiertes Datenscreening auf Basis öffentlich verfügbarer Fernerkundungs- und Bodendaten (Copernicus EGMS, LUCAS, SoilGrids). Er ersetzt keine Ortsbesichtigung, Laboranalyse oder fachliche Einzelfallbewertung durch einen zugelassenen Sachverständigen gem. §18 BBodSchG. Messwerte basieren auf regionalen Durchschnittswerten und nicht auf standortspezifischen Beprobungen.
  <br><br>
  <em>Generated using European Union's Copernicus Land Monitoring Service information.</em>
</div>

<div class="footer">
  <div class="brand">Bodenbericht</div>
  <div>Standort-Screening · bodenbericht.de</div>
  <div style="margin-top:2px; opacity:.6;">© {now.year} Bodenbericht · Ein Service der {escape(operator_legal_name)}</div>
  <div style="margin-top:2px; opacity:.6;">Impressum: <a href="{escape(operator_imprint_url)}" style="color:inherit;">{escape(operator_imprint_url.replace('https://', '').replace('http://', ''))}</a></div>
</div>

</div></body></html>"""
