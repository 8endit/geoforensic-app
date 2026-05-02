"""V.4 — End-to-end Vollbericht (HTML→Chrome-Headless).

Builds the GeoForensic Vollbericht with the Schulstraße-12 example
inputs and verifies it renders to a non-trivial PDF. Live test —
spawns Chrome subprocess, may fetch CartoDB tiles.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.full_report import (
    _build_data_sources_list,
    _build_block_pills,
    _font_face_css,
    _qr_svg,
    generate_full_report,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_PAYLOAD = REPO_ROOT / "docs" / "visuals" / "example_payload.json"


@pytest.fixture(scope="module")
def example_payload() -> dict:
    return json.loads(EXAMPLE_PAYLOAD.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Helper-function unit tests
# ---------------------------------------------------------------------------

def test_font_face_css_includes_all_four_fonts() -> None:
    css = _font_face_css()
    assert "Sentient" in css
    assert "Geist Mono" in css
    # Two weights of each → four @font-face blocks
    assert css.count("@font-face") == 4
    assert "data:font/woff2;base64," in css


def test_qr_svg_returns_inline_svg_string() -> None:
    qr = _qr_svg("GF-TEST-FAKE-ID")
    assert qr is not None
    assert qr.startswith("<svg")
    assert "</svg>" in qr


def test_data_sources_list_skips_unavailable_modules() -> None:
    sources = _build_data_sources_list(
        has_egms=True, has_soil=True, has_kostra=False, has_flood=False,
        has_mining=False, has_slope=True, has_altlasten=False,
        has_pesticides=False, has_geology=True, has_basemap=True,
    )
    names = {s["name"] for s in sources}
    assert any("EGMS" in n for n in names)
    assert any("SoilGrids" in n for n in names)
    assert any("BGR GÜK250" in n for n in names)
    assert any("CartoDB" in n for n in names)
    assert not any("KOSTRA" in n for n in names)
    assert not any("BfG" in n for n in names)


def test_block_pills_have_four_entries() -> None:
    payload = {"components": {"risk_dashboard": {"burland_label": "leicht", "overall_grade": "B"}}}
    pills = _build_block_pills(
        payload, flood_data=None, kostra_data=None, mining_data=None,
        slope_data=None, altlasten_data=None, pesticides_data=None,
        soil_directive_data=None,
    )
    assert set(pills.keys()) == {1, 2, 3, 4}
    for block in pills.values():
        assert len(block) >= 2


# ---------------------------------------------------------------------------
# Full render test (live)
# ---------------------------------------------------------------------------

def _example_inputs(example_payload: dict) -> dict:
    """Build the kwargs for ``generate_full_report`` from the
    Schulstraße-12 example payload."""
    components = example_payload["components"]
    psi_pts = components["property_context_map"]["psi_points"]
    velocities = [p["velocity"] for p in psi_pts]
    return {
        "address": example_payload["address"]["full"],
        "lat": example_payload["address"]["lat"],
        "lon": example_payload["address"]["lon"],
        "ampel": "gelb",
        "point_count": len(psi_pts),
        "mean_velocity": sum(velocities) / len(velocities),
        "max_velocity": min(velocities, key=lambda v: v),  # most negative
        "geo_score": 72,
        "soil_profile": {
            "soilgrids": {
                "soc": 18, "phh2o": 64,
                "clay": 220, "sand": 510, "silt": 270,
                "bdod": 142,
            },
            "metals": {"cd": 0.3, "pb": 28, "as": 8, "cu": 18, "zn": 65, "cr": 24, "ni": 18},
            "metal_status": {
                "cd": "stabil", "pb": "stabil", "as": "stabil",
                "cu": "stabil", "zn": "stabil", "cr": "stabil", "ni": "stabil",
            },
            "nutrients": {"n": 1.7, "p": 28, "k": 145, "caco3": 1.2},
            "lucas_distance_km": 5.4,
            "imperviousness": components["soil_context_stack"]["sealing_percent"],
            "soil_layers": components["soil_context_stack"]["layers"],
            "groundwater_depth_m": components["soil_context_stack"]["groundwater_depth_m"],
        },
        "answers": {},
        "psi_points": psi_pts,
        "psi_timeseries": components["velocity_timeseries"]["psi_series"],
        "precipitation_series": components["velocity_timeseries"]["precipitation_series"],
        "annual_precipitation_mm": 835,
        "geology_data": {
            "available": True,
            "rock_type_short": "Buntsandstein",
            "stratigraphy": "Mittlerer Buntsandstein",
            "data_provenance": {"source": "BGR GÜK250", "resolution_m": 250},
        },
        "building_footprint_data": {
            "available": True,
            "polygon": components["property_context_map"]["building_footprint"]["polygon"],
            "centroid": components["property_context_map"]["building_footprint"]["centroid"],
        },
        "flood_data": {
            "available": True,
            "any_affected": False,
            "scenarios": {
                "hq_haeufig": {"affected": False},
                "hq_100": {"affected": False},
                "hq_extrem": {"affected": True},
            },
        },
        "kostra_data": {
            "available": True,
            "region": "Murgtal",
            "statistics": {
                "intensity_60min_T100": 38.2,
                "intensity_15min_T100": 22.1,
                "intensity_60min_T20": 26.8,
            },
        },
        "mining_data": {"available": True, "hits": [], "search_radius_m": 500},
        "slope_data": {
            "available": True,
            "slope_deg": 4.2,
            "elevation_m": 156,
            "aspect_label": "SO",
            "classification": "leicht geneigt",
            "scale_m": 50,
        },
        "altlasten_data": {
            "available": True,
            "source": "corine-proxy",
            "land_use": {
                "clc_label": "Discontinuous urban fabric",
                "clc_code": 112,
                "industry_share_pct": 2.1,
            },
        },
        "pesticides_data": {
            "available": True,
            "regional_scope": "NUTS2 DE12",
            "detected_count": 7,
            "total_residue_mg_per_kg": 0.045,
            "top_substance": "Glyphosat",
        },
        "soil_directive_data": {
            "descriptors_total": 13,
            "descriptors_determined": 1,
            "descriptors_not_remote": 0,
            "descriptors_not_available": 12,
            "overall_status": "gesund",
            "part_a": {
                "soc_concentration": {
                    "label": "Verlust organischer Substanz (SOC-Konzentration)",
                    "annex_descriptor": "Loss of Soil Organic Carbon (concentration)",
                    "value": 18.5, "unit": "g/kg",
                    "status": "ok", "status_label": "Innerhalb Schwelle",
                    "source": "SoilGrids 250m + LUCAS Topsoil",
                },
            },
        },
        "country_code": "de",
        "report_id": "GF-V4-E2E-DEMO",
        "fetch_basemap_tiles": False,  # offline-safe by default
    }


def test_render_html_offline_produces_well_formed_doc(example_payload: dict) -> None:
    """Without going through Chrome, verify the assembled HTML is
    syntactically valid and contains all the expected blocks."""
    from app.full_report import render_full_report_html
    kwargs = _example_inputs(example_payload)
    html = render_full_report_html(**kwargs)
    # Cover present
    assert 'class="cover"' in html
    # All 4 blocks present
    for n in (1, 2, 3, 4):
        assert f"Block {n:02d}" in html
    # All 12 sections present (look for h2 with the section titles)
    for title in (
        "1 · Bodenbewegung",
        "2 · Hochwasser",
        "3 · Starkregen",
        "4 · Geländeprofil",
        "5 · Bergbau",
        "6 · Altlasten",
        "7 · Bodenqualität",
        "8 · Schwermetalle",
        "9 · Nährstoff",
        "10 · Pestizid",
        "11 · EU Soil Monitoring",
        "12 · Individuelle Einschätzung",
    ):
        assert title in html, f"missing section heading: {title}"
    # Provenance page
    assert "Datenquellen" in html
    # Fonts embedded
    assert "@font-face" in html
    assert "Sentient" in html
    # Visuals embedded as inline SVG
    assert html.count("<svg") >= 6  # at least 6 component SVGs (cover QR + 6 visuals)


def test_render_html_includes_address_on_cover(example_payload: dict) -> None:
    from app.full_report import render_full_report_html
    kwargs = _example_inputs(example_payload)
    html = render_full_report_html(**kwargs)
    assert "Schulstraße 12, 76571 Gaggenau" in html
    assert "GF-V4-E2E-DEMO" in html


@pytest.mark.live
def test_v4_e2e_full_pdf_render(example_payload: dict) -> None:
    """V.4 acceptance: the Schulstraße-12 inputs render to a real PDF
    via Chrome-Headless, with all 6 visuals as inline SVG."""
    from app.pdf_renderer import _find_chrome
    if _find_chrome() is None:
        pytest.skip("Chrome/Chromium not available")

    kwargs = _example_inputs(example_payload)
    # Enable basemap fetch for the headline live test
    kwargs["fetch_basemap_tiles"] = True

    pdf = generate_full_report(**kwargs)
    assert pdf is not None
    assert pdf.startswith(b"%PDF-")
    # 6 SVGs + cover + 12 sections → expect a sizeable PDF
    assert len(pdf) > 80_000
    # Acceptance budget from the plan: < 1.5 MB
    assert len(pdf) < 1_500_000, f"PDF size {len(pdf)} exceeds 1.5 MB budget"

    # Persist for manual inspection
    out_dir = Path(__file__).resolve().parent / "_artifacts"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "v4_full_report.pdf").write_bytes(pdf)


@pytest.mark.live
def test_v4_persists_html_for_inspection(example_payload: dict) -> None:
    """Write the assembled HTML next to the PDF so we can open it in a
    browser without Chrome-Headless and tweak CSS visually."""
    from app.full_report import render_full_report_html
    kwargs = _example_inputs(example_payload)
    html = render_full_report_html(**kwargs)
    out_dir = Path(__file__).resolve().parent / "_artifacts"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "v4_full_report.html").write_text(html, encoding="utf-8")
    assert "<title>" in html
