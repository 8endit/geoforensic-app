"""Vollbericht renderer — Chrome-Headless HTML→PDF pipeline.

Refactored 2026-05-01 from FPDF (V.4 of the Visuals Sprint). Layout
now lives in CSS Paged Media (``backend/static/css/full_report.css``)
and Jinja2 HTML templates under ``backend/templates/full_report/``.

Public API
----------
``generate_full_report(...)`` keeps the same signature as the old FPDF
version so ``routers/leads.py`` does not need to change. Internally:

  1. Build the visuals payload from the raw inputs.
  2. Render all six SVG visuals.
  3. Build per-section HTML blocks (cover → 4 thematic blocks → 12
     sections → data sources page).
  4. Stitch into the base template, embed @font-face data: URIs,
     pipe through ``pdf_renderer.html_to_pdf``.

Design system: Cozy (schwarz / grün / Sentient + Geist Mono). The
free-tier teaser PDF still flows through ``html_report.py``; this file
is the Premium ``geoforensic.de`` artefact.
"""

from __future__ import annotations

import base64
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.basemap import build_map_render_context, fetch_basemap
from app.chart_helpers import (
    build_histogram_render_context,
    build_radar_render_context,
    build_soil_stack_render_context,
    build_timeseries_render_context,
)
from app.pdf_renderer import html_to_pdf
from app.visual_payload import build_payload
from app.visual_renderer import load_tokens, render_svg

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_ROOT.parent

FULL_REPORT_TEMPLATES = _BACKEND_ROOT / "templates" / "full_report"
FONTS_DIR = _BACKEND_ROOT / "static" / "fonts"
CSS_DIR = _BACKEND_ROOT / "static" / "css"


# ---------------------------------------------------------------------------
# Jinja env
# ---------------------------------------------------------------------------

def _full_report_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(FULL_REPORT_TEMPLATES)),
        autoescape=select_autoescape(["html"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


# ---------------------------------------------------------------------------
# Font + CSS embedding
# ---------------------------------------------------------------------------

def _font_face_css() -> str:
    """Build @font-face declarations with base64 data: URIs.

    Embeds the four subset woff2 files produced by
    ``scripts/subset_fonts.py``. Total payload ~70 KB.
    """
    pairs: list[tuple[str, str, int, str, str]] = [
        # filename, family, weight, style, source name
        ("sentient-extralight.woff2",  "Sentient",   200, "normal", "Sentient Extralight"),
        ("sentient-lightitalic.woff2", "Sentient",   300, "italic", "Sentient Light Italic"),
        ("geist-mono-regular.woff2",   "Geist Mono", 400, "normal", "Geist Mono Regular"),
        ("geist-mono-medium.woff2",    "Geist Mono", 500, "normal", "Geist Mono Medium"),
    ]
    blocks: list[str] = []
    for fname, family, weight, style, _label in pairs:
        path = FONTS_DIR / fname
        if not path.exists():
            logger.warning("font missing for full_report embed: %s", path)
            continue
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        blocks.append(
            f"@font-face {{ font-family: '{family}'; font-weight: {weight}; "
            f"font-style: {style}; "
            f"src: url('data:font/woff2;base64,{b64}') format('woff2'); }}"
        )
    return "\n".join(blocks)


def _read_css_inline() -> tuple[str, str]:
    """Return (tokens_css_inlined, full_report_css_inlined) as data: URIs.

    We inline both CSS files so Chrome doesn't depend on file:// resolution.
    """
    tokens_css = (CSS_DIR / "tokens.css").read_text(encoding="utf-8")
    fr_css = (CSS_DIR / "full_report.css").read_text(encoding="utf-8")
    # full_report.css does @import url("./tokens.css") — inline that
    # explicitly so we can serve everything in one document.
    fr_css_no_import = re.sub(
        r'@import\s+url\([^)]+\);\s*', "", fr_css, count=1
    )
    tokens_uri = "data:text/css;base64," + base64.b64encode(
        tokens_css.encode("utf-8")
    ).decode("ascii")
    fr_uri = "data:text/css;base64," + base64.b64encode(
        fr_css_no_import.encode("utf-8")
    ).decode("ascii")
    return tokens_uri, fr_uri


# ---------------------------------------------------------------------------
# QR code (provenance link on the cover)
# ---------------------------------------------------------------------------

def _qr_svg(report_id: str, base_url: str = "https://geoforensic.de") -> Optional[str]:
    """Render a small QR pointing at the provenance page for the report.

    Returns ``None`` if ``segno`` is missing — the cover renders
    without a QR in that case.
    """
    try:
        import io
        import segno
    except ImportError:  # pragma: no cover
        return None
    url = f"{base_url}/r/{report_id}"
    qr = segno.make(url, error="m")
    bio = io.BytesIO()
    qr.save(bio, kind="svg", scale=8, border=0,
            dark="#000000", light="#FFFFFF", xmldecl=False)
    return bio.getvalue().decode("utf-8")


# ---------------------------------------------------------------------------
# Datasource list for the provenance page
# ---------------------------------------------------------------------------

def _build_data_sources_list(
    *,
    has_egms: bool,
    has_soil: bool,
    has_kostra: bool,
    has_flood: bool,
    has_mining: bool,
    has_slope: bool,
    has_altlasten: bool,
    has_pesticides: bool,
    has_geology: bool,
    has_basemap: bool,
) -> list[dict]:
    """Build the list of data-source rows for the last page."""
    out: list[dict] = []

    if has_egms:
        out.append({
            "name": "European Ground Motion Service (EGMS)",
            "license": "CC BY 4.0",
            "url": "https://egms.land.copernicus.eu/",
            "resolution_m": 100,
            "method": "PostGIS spatial query, 500 m radius",
            "note": "Sentinel-1 InSAR L3, 7,92 Mio Punkte DE + 3,25 Mio Punkte NL (Stand 2026-05). AT/CH-Coverage in Vorbereitung.",
        })
    if has_soil:
        out.append({
            "name": "ISRIC SoilGrids 250 m",
            "license": "CC BY 4.0",
            "url": "https://www.isric.org/explore/soilgrids",
            "resolution_m": 250,
            "method": "Single-Pixel-Lookup",
        })
        out.append({
            "name": "JRC ESDAC LUCAS Topsoil 2018",
            "license": "EU Open Data",
            "url": "https://esdac.jrc.ec.europa.eu/projects/lucas",
            "method": "Nearest-Point-Match (Country-Gate DE; NL/AT/CH bewusst inaktiv)",
        })
        out.append({
            "name": "Copernicus CORINE Land Cover 2018",
            "license": "Copernicus Free, Full and Open Policy",
            "url": "https://land.copernicus.eu/pan-european/corine-land-cover",
            "resolution_m": 100,
            "method": "Window-Mean 100 m",
        })
        out.append({
            "name": "Copernicus HRL Imperviousness 2021",
            "license": "Copernicus FFO",
            "url": "https://land.copernicus.eu/pan-european/high-resolution-layers/imperviousness",
            "resolution_m": 20,
            "method": "Window-Mean 100 m",
            "note": "DE-Bounds; NL liefert NODATA.",
        })
    if has_geology:
        out.append({
            "name": "BGR GÜK250 (Geologische Übersichtskarte)",
            "license": "BGR Service",
            "url": "https://services.bgr.de/arcgis/rest/services/geologie/guek250/MapServer",
            "resolution_m": 250,
            "method": "ArcGIS REST identify, point-in-polygon (DE only)",
        })
    if has_kostra:
        out.append({
            "name": "DWD KOSTRA-DWD-2020",
            "license": "GeoNutzV",
            "url": "https://www.dwd.de/DE/leistungen/kostra_dwd_rasterwerte/kostra_dwd_rasterwerte.html",
            "method": "GeoTIFF-Lookup (Bemessungsregenhöhen 1991–2020)",
        })
    if has_flood:
        out.append({
            "name": "BfG Hochwasserrisikomanagement-Richtlinie (HWRM-RL)",
            "license": "DL-DE/Zero-2.0",
            "url": "https://geoportal.bafg.de/inspire/",
            "method": "WMS GetFeatureInfo, 3 Szenarien (HQ häufig / 100 / extrem)",
        })
    if has_mining:
        out.append({
            "name": "Bezirksregierung Arnsberg — Bergbauberechtigungen NRW",
            "license": "DL-DE/by-2.0",
            "url": "https://www.bra.nrw.de/",
            "method": "WMS GetFeatureInfo, 500 m Radius (NRW only)",
        })
    if has_slope:
        out.append({
            "name": "OpenTopoData (SRTM 1-arcsec)",
            "license": "Public Domain (SRTM) / MIT (OpenTopoData)",
            "url": "https://www.opentopodata.org/",
            "resolution_m": 30,
            "method": "Multi-Scale-Steepest aus 4-Punkt-Probes (50 m / 150 m / 500 m)",
        })
    if has_altlasten:
        out.append({
            "name": "PDOK Bodemloket / CORINE-Proxy (Altlasten-Indikator)",
            "license": "CC BY 4.0 / Copernicus FFO",
            "url": "https://www.bodemloket.nl/",
            "method": "NL: PDOK WBB-Lokationen · DE: CORINE-Proxy + Behörden-Verweis",
        })
    if has_pesticides:
        out.append({
            "name": "JRC LUCAS Pesticides 2018 (NUTS2-Aggregat)",
            "license": "EU Open Data",
            "url": "https://esdac.jrc.ec.europa.eu/projects/lucas",
            "method": "Eurostat NUTS-2021 Region-Match",
        })
    if has_basemap:
        out.append({
            "name": "CartoDB Positron (Basemap)",
            "license": "CC BY 3.0",
            "url": "https://carto.com/attributions",
            "method": "Tile-Composite mit OpenStreetMap-Daten · Attribution: © OSM contributors © CARTO",
        })
    out.append({
        "name": "OpenStreetMap (Building Footprints via Overpass)",
        "license": "ODbL",
        "url": "https://www.openstreetmap.org/copyright",
        "method": "Overpass `way[building]`, addr:housenumber + addr:postcode tag match",
    })
    return out


# ---------------------------------------------------------------------------
# Block status pills (for the trenn-Seiten)
# ---------------------------------------------------------------------------

def _block_pill(label: str, ampel: str | None = None) -> dict:
    return {"label": label, "ampel": ampel or "none"}


def _build_block_pills(
    payload: dict,
    flood_data: Optional[dict],
    kostra_data: Optional[dict],
    mining_data: Optional[dict],
    slope_data: Optional[dict],
    altlasten_data: Optional[dict],
    pesticides_data: Optional[dict],
    soil_directive_data: Optional[dict],
) -> dict[int, list[dict]]:
    """Compute the status pills shown on each block-separator page."""
    rd = payload["components"]["risk_dashboard"]
    ampel_label = rd.get("burland_label") or "stabil"

    return {
        1: [
            _block_pill(f"Bodenbewegung · {ampel_label}", ampel_label),
            _block_pill("Hochwasser",  "auffaellig" if flood_data and flood_data.get("any_affected") else "stabil"),
            _block_pill("Starkregen",  "stabil" if (kostra_data or {}).get("available") else "none"),
        ],
        2: [
            _block_pill("Geländeprofil", "stabil" if (slope_data or {}).get("available") else "none"),
            _block_pill("Bergbau", "auffaellig" if (mining_data or {}).get("hits") else "stabil"),
            _block_pill("Altlasten", "moderat" if (altlasten_data or {}).get("hit_count", 0) > 0 else "stabil"),
        ],
        3: [
            _block_pill("Bodenqualität", "stabil"),
            _block_pill("Schwermetalle", "stabil"),
            _block_pill("Nährstoffe", "stabil"),
            _block_pill("Pestizide", "stabil" if (pesticides_data or {}).get("available") else "none"),
        ],
        4: [
            _block_pill(
                f"EU 2025/2360 · {(soil_directive_data or {}).get('descriptors_total', 13)} Descriptoren + 4 Sealing",
                "stabil" if soil_directive_data else "none",
            ),
            _block_pill(f"Gesamtnote {rd.get('overall_grade', '—')}", ampel_label),
        ],
    }


# ---------------------------------------------------------------------------
# Top-level: generate_full_report
# ---------------------------------------------------------------------------

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
    # Soil data (legacy aggregator: soilgrids/metals/nutrients/...)
    soil_profile: dict,
    answers: dict | None = None,
    mining_data: dict | None = None,
    kostra_data: dict | None = None,
    flood_data: dict | None = None,
    soil_directive_data: dict | None = None,
    altlasten_data: dict | None = None,
    slope_data: dict | None = None,
    country_code: str = "de",
    # New optional inputs (V.0.x): if the caller fetched them, use them;
    # otherwise the report falls back to defaults.
    psi_points: list[dict] | None = None,
    psi_timeseries: list[dict] | None = None,
    precipitation_series: list[dict] | None = None,
    geology_data: dict | None = None,
    building_footprint_data: dict | None = None,
    pesticides_data: dict | None = None,
    annual_precipitation_mm: float | None = None,
    report_id: str | None = None,
    fetch_basemap_tiles: bool = True,
) -> bytes:
    """Render the GeoForensic Vollbericht to PDF bytes via Chrome-Headless.

    Signature is backwards-compatible with the FPDF predecessor; new
    optional kwargs let the caller pass the V.0.x outputs (PSI series,
    geology, building footprint) directly. Missing inputs are tolerated
    — sections render a "Daten in Vorbereitung" placeholder.
    """
    issued_dt = datetime.now(timezone.utc)
    report_id = report_id or f"BB-{issued_dt.strftime('%Y-%m-%d-%H%M%S')}"

    # ── 1. Build the visuals payload ───────────────────────────────────
    address_dict = {
        "full": address,
        "lat": lat,
        "lon": lon,
    }
    sg = (soil_profile or {}).get("soilgrids", {})
    sealing_pct = (soil_profile or {}).get("imperviousness")
    payload = build_payload(
        address=address_dict,
        psi_points=psi_points or [],
        psi_timeseries=psi_timeseries or [],
        precipitation_series=precipitation_series,
        annual_precipitation_mm=annual_precipitation_mm,
        sealing_percent=sealing_pct,
        clay_percent=(sg.get("clay") / 10.0) if sg.get("clay") else None,
        slope_degrees=(slope_data or {}).get("slope_deg"),
        groundwater_depth_m=(soil_profile or {}).get("groundwater_depth_m"),
        soil_layers=(soil_profile or {}).get("soil_layers"),
        building_footprint=building_footprint_data,
        geology=geology_data,
        radius_meters=500,
        tier="premium",
        report_id=report_id,
    )

    # ── 2. Fetch basemap (optional, slow) ──────────────────────────────
    basemap = None
    if fetch_basemap_tiles:
        try:
            basemap = fetch_basemap(lat, lon, radius_m=500, width_px=600, height_px=320)
        except Exception:  # noqa: BLE001
            logger.exception("basemap fetch failed; falling back to grey")
            basemap = None

    # ── 3. Render the six SVG visuals ──────────────────────────────────
    tokens = load_tokens()
    rd_svg = render_svg("risk_dashboard", payload["components"]["risk_dashboard"])
    map_ctx = build_map_render_context(
        payload["components"]["property_context_map"],
        address_lat=lat, address_lon=lon, basemap=basemap, tokens=tokens,
    )
    map_svg = render_svg("property_context_map",
                         payload["components"]["property_context_map"], map=map_ctx)
    ts_ctx = build_timeseries_render_context(payload["components"]["velocity_timeseries"])
    ts_svg = render_svg("velocity_timeseries",
                        payload["components"]["velocity_timeseries"], chart=ts_ctx)
    soil_ctx = build_soil_stack_render_context(
        payload["components"]["soil_context_stack"], tokens=tokens,
    )
    soil_svg = render_svg("soil_context_stack",
                          payload["components"]["soil_context_stack"], stack=soil_ctx)
    radar_ctx = build_radar_render_context(payload["components"]["correlation_radar"])
    radar_svg = render_svg("correlation_radar",
                           payload["components"]["correlation_radar"], radar=radar_ctx)
    hist_ctx = build_histogram_render_context(
        payload["components"]["neighborhood_histogram"], tokens=tokens,
    )
    hist_svg = render_svg("neighborhood_histogram",
                          payload["components"]["neighborhood_histogram"], hist=hist_ctx)

    # ── 4. Render each HTML block ──────────────────────────────────────
    env = _full_report_env()
    issued_at = issued_dt.astimezone().strftime("%d.%m.%Y · %H:%M")
    qr_svg = _qr_svg(report_id)

    pills = _build_block_pills(
        payload, flood_data, kostra_data, mining_data, slope_data,
        altlasten_data, pesticides_data, soil_directive_data,
    )

    cover_html = env.get_template("cover.html").render(
        payload=payload, qr_svg=qr_svg, issued_at=issued_at,
        # "Ihr Standort in 5 Punkten"-Cover-Summary nutzt diese Aggregate
        flood_data=flood_data,
        mining_data=mining_data,
        soil_directive_data=soil_directive_data,
        soil_profile=soil_profile,
    )

    block1 = env.get_template("block_separator.html").render(
        block_num=1,
        block_title="Bodenrisiken aus Satellit & Wetter",
        block_desc="Sentinel-1 InSAR-Streupunkte, BfG Hochwasser-Szenarien und DWD-Starkregenstatistik.",
        pills=pills[1],
    )
    s01 = env.get_template("section_01_bodenbewegung.html").render(
        payload=payload, rd_svg=rd_svg, map_svg=map_svg, ts_svg=ts_svg,
    )
    s02 = env.get_template("section_02_hochwasser.html").render(flood_data=flood_data)
    s03 = env.get_template("section_03_kostra.html").render(kostra_data=kostra_data)

    block2 = env.get_template("block_separator.html").render(
        block_num=2,
        block_title="Untergrund & Topographie",
        block_desc="Geländeprofil, Bergbau-Altrechte und Altlasten-Indikator.",
        pills=pills[2],
    )
    s04 = env.get_template("section_04_slope.html").render(slope_data=slope_data)
    s05 = env.get_template("section_05_bergbau.html").render(mining_data=mining_data)
    s06 = env.get_template("section_06_altlasten.html").render(altlasten_data=altlasten_data)

    block3 = env.get_template("block_separator.html").render(
        block_num=3,
        block_title="Bodenchemie",
        block_desc="Bodenaufbau, Schwermetalle, Nährstoffe und Pestizid-Hintergrundwerte.",
        pills=pills[3],
    )
    s07 = env.get_template("section_07_bodenqualitaet.html").render(
        payload=payload, soil_profile=soil_profile, soil_stack_svg=soil_svg,
    )
    s08 = env.get_template("section_08_schwermetalle.html").render(soil_profile=soil_profile)
    s09 = env.get_template("section_09_naehrstoffe.html").render(soil_profile=soil_profile)
    s10 = env.get_template("section_10_pestizide.html").render(pesticides_data=pesticides_data)

    block4 = env.get_template("block_separator.html").render(
        block_num=4,
        block_title="Gesamt-Bewertung",
        block_desc="EU Soil Monitoring Directive 2025/2360 und individuelle Profil-Synthese.",
        pills=pills[4],
    )
    s11 = env.get_template("section_11_eu_directive.html").render(
        soil_directive_data=soil_directive_data,
    )
    s12 = env.get_template("section_12_einschaetzung.html").render(
        payload=payload, radar_svg=radar_svg, hist_svg=hist_svg,
    )

    sources = _build_data_sources_list(
        has_egms=point_count > 0,
        has_soil=bool(soil_profile),
        has_kostra=bool(kostra_data and kostra_data.get("available")),
        has_flood=bool(flood_data and flood_data.get("available")),
        has_mining=bool(mining_data and mining_data.get("available")),
        has_slope=bool(slope_data and slope_data.get("available")),
        has_altlasten=bool(altlasten_data and altlasten_data.get("available")),
        has_pesticides=bool(pesticides_data and pesticides_data.get("available")),
        has_geology=bool(geology_data and geology_data.get("available")),
        has_basemap=bool(basemap and basemap.get("available")),
    )
    data_sources_html = env.get_template("data_sources.html").render(
        payload=payload, sources=sources,
    )

    body_blocks = "\n".join([
        cover_html,
        block1, s01, s02, s03,
        block2, s04, s05, s06,
        block3, s07, s08, s09, s10,
        block4, s11, s12,
        data_sources_html,
    ])

    # ── 5. Wrap in base.html with embedded CSS + fonts ────────────────
    tokens_uri, fr_uri = _read_css_inline()
    fonts_css = _font_face_css()

    html = env.get_template("base.html").render(
        payload=payload,
        body_blocks=body_blocks,
        fonts_css=fonts_css,
        tokens_css_url=tokens_uri,
        full_report_css_url=fr_uri,
    )

    # ── 6. Render PDF ──────────────────────────────────────────────────
    pdf_bytes = html_to_pdf(html)
    if pdf_bytes is None:
        raise RuntimeError(
            "Vollbericht render failed — neither Chrome-Headless nor "
            "WeasyPrint produced a PDF. Check pdf_renderer logs."
        )
    return pdf_bytes


def render_full_report_html(
    address: str,
    lat: float,
    lon: float,
    **kwargs: Any,
) -> str:
    """Same as ``generate_full_report`` but returns the raw HTML.

    Useful for debugging the layout in a browser without going through
    Chrome-Headless. Not used in production.
    """
    # Re-implement the body of generate_full_report up to the html string
    # by calling it with a fake renderer. The simplest path: monkey-patch
    # html_to_pdf to capture the HTML. For now, delegate via a flag.
    import app.full_report as self_mod
    captured: dict[str, str] = {}
    orig = self_mod.html_to_pdf

    def fake_html_to_pdf(html: str) -> bytes:
        captured["html"] = html
        return b"%PDF-1.4 stub"

    self_mod.html_to_pdf = fake_html_to_pdf  # type: ignore[assignment]
    try:
        generate_full_report(address, lat, lon, **kwargs)
        return captured.get("html", "")
    finally:
        self_mod.html_to_pdf = orig  # type: ignore[assignment]
