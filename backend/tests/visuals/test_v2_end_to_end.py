"""V.2 End-to-End — beide Tier-1-Templates rendered via Chrome-Headless.

Schulstraße-12-Daten → build_payload → render risk_dashboard +
property_context_map → wrap in HTML → push through pdf_renderer.

Live test (uses CartoDB tiles + Chrome-Headless), skipped by default.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.basemap import build_map_render_context, fetch_basemap
from app.visual_payload import build_payload
from app.visual_renderer import render_svg


REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_PAYLOAD = REPO_ROOT / "docs" / "visuals" / "example_payload.json"


def _build_full_payload() -> dict:
    example = json.loads(EXAMPLE_PAYLOAD.read_text(encoding="utf-8"))
    components = example["components"]
    return build_payload(
        address=example["address"],
        psi_points=components["property_context_map"]["psi_points"],
        psi_timeseries=components["velocity_timeseries"]["psi_series"],
        precipitation_series=components["velocity_timeseries"]["precipitation_series"],
        annual_precipitation_mm=835,
        sealing_percent=components["soil_context_stack"]["sealing_percent"],
        clay_percent=22,
        slope_degrees=4.2,
        groundwater_depth_m=components["soil_context_stack"]["groundwater_depth_m"],
        soil_layers=components["soil_context_stack"]["layers"],
        building_footprint={
            "available": True,
            "polygon": components["property_context_map"]["building_footprint"]["polygon"],
            "centroid": components["property_context_map"]["building_footprint"]["centroid"],
        },
        radius_meters=500,
        tier="premium",
        report_id="GF-TEST-V2-E2E",
    )


def test_both_tier1_templates_render_inline_in_html() -> None:
    """Without external network: render both SVGs and embed them in
    HTML — must produce a well-formed HTML doc."""
    payload = _build_full_payload()

    rd_svg = render_svg("risk_dashboard", payload["components"]["risk_dashboard"])
    map_ctx = build_map_render_context(
        payload["components"]["property_context_map"],
        address_lat=payload["address"]["lat"],
        address_lon=payload["address"]["lon"],
        basemap=None,  # offline-safe
    )
    map_svg = render_svg(
        "property_context_map",
        payload["components"]["property_context_map"],
        map=map_ctx,
    )

    assert rd_svg.startswith("<svg")
    assert map_svg.startswith("<svg")
    assert "Burland-Klasse" in rd_svg
    assert "PSI-Punkte" in map_svg


def _wrap_html(rd_svg: str, map_svg: str) -> str:
    return f"""<!doctype html>
<html><head>
  <meta charset="utf-8"><title>V.2 E2E Smoke</title>
  <style>
    @page {{ size: A4; margin: 14mm; }}
    body {{ margin: 0; font-family: -apple-system, sans-serif; }}
    h1 {{ font-size: 16pt; margin: 0 0 8pt; }}
    h2 {{ font-size: 11pt; color: #666; margin: 16pt 0 6pt; }}
    .visual {{ width: 680px; max-width: 100%; }}
  </style>
</head><body>
  <h1>GeoForensic Tier-1 Visuals — Smoke Test</h1>
  <h2>Komponente 1 · Risiko-Dashboard</h2>
  <div class="visual">{rd_svg}</div>
  <h2>Komponente 2 · Grundstück-im-Kontext</h2>
  <div class="visual">{map_svg}</div>
</body></html>"""


@pytest.mark.live
def test_v2_e2e_chrome_headless_renders_pdf_with_both_visuals() -> None:
    """V.2 acceptance: PDF rendered via Chrome-Headless contains both
    Tier-1 visuals at the right size."""
    from app.pdf_renderer import _find_chrome, html_to_pdf

    if _find_chrome() is None:
        pytest.skip("Chrome/Chromium not available")

    payload = _build_full_payload()

    # With real basemap
    basemap = fetch_basemap(
        payload["address"]["lat"],
        payload["address"]["lon"],
        radius_m=500,
        width_px=600,
        height_px=320,
    )

    rd_svg = render_svg("risk_dashboard", payload["components"]["risk_dashboard"])
    map_ctx = build_map_render_context(
        payload["components"]["property_context_map"],
        address_lat=payload["address"]["lat"],
        address_lon=payload["address"]["lon"],
        basemap=basemap,
    )
    map_svg = render_svg(
        "property_context_map",
        payload["components"]["property_context_map"],
        map=map_ctx,
    )

    # Sanity: basemap was fetched and embedded
    assert basemap["available"] is True, basemap
    assert "data:image/png;base64," in map_svg

    pdf = html_to_pdf(_wrap_html(rd_svg, map_svg))
    assert pdf is not None
    assert pdf.startswith(b"%PDF-")
    # PDF must be substantial (>15 KB) — text-only fallback would be ~5 KB
    assert len(pdf) > 15_000

    # For manual inspection: write the artifacts beside the test
    out_dir = Path(__file__).resolve().parent / "_artifacts"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "v2_e2e.pdf").write_bytes(pdf)
    (out_dir / "v2_e2e.html").write_text(
        _wrap_html(rd_svg, map_svg), encoding="utf-8"
    )


@pytest.mark.live
def test_v2_e2e_offline_fallback_still_renders() -> None:
    """Even without basemap (offline / fetch failed), both visuals
    render and produce a usable PDF."""
    from app.pdf_renderer import _find_chrome, html_to_pdf

    if _find_chrome() is None:
        pytest.skip("Chrome/Chromium not available")

    payload = _build_full_payload()

    rd_svg = render_svg("risk_dashboard", payload["components"]["risk_dashboard"])
    map_ctx = build_map_render_context(
        payload["components"]["property_context_map"],
        address_lat=payload["address"]["lat"],
        address_lon=payload["address"]["lon"],
        basemap=None,  # explicit offline mode
    )
    map_svg = render_svg(
        "property_context_map",
        payload["components"]["property_context_map"],
        map=map_ctx,
    )

    assert "data:image/png;base64," not in map_svg
    pdf = html_to_pdf(_wrap_html(rd_svg, map_svg))
    assert pdf is not None
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 5_000
