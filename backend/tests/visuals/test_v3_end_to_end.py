"""V.3 End-to-End — alle 6 Visuals plus Tier-2-Teaser via Chrome-Headless.

Two PDFs are produced (live test):
  - "Premium" view: all 6 visuals fully rendered
  - "Free / teaser" view: Tier-1 visuals full, Tier-2 wrapped in
    teaser (blur + lock overlay)

Both must render through pdf_renderer.html_to_pdf without errors.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.basemap import build_map_render_context
from app.chart_helpers import (
    build_histogram_render_context,
    build_radar_render_context,
    build_soil_stack_render_context,
    build_timeseries_render_context,
)
from app.visual_payload import build_payload
from app.visual_renderer import load_tokens, render_svg, wrap_teaser


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
        report_id="GF-TEST-V3-E2E",
    )


def _render_all_six(payload: dict, tier: str) -> dict[str, str]:
    """Render every component to its inline SVG.

    For ``tier='free'`` the Tier-2 components (3, 4, 5, 6 — well
    actually per spec 3, 4, 5, 6 but #3 + #6 are Tier-1 in the spec
    table; only #4 and #5 are Tier-2. The spec table also has #3 + #6
    as Tier-1 voll im Free, with Teaser only on #4 + #5. Let me
    re-read…) — actually SPEC §1 table marks #3 #4 #5 #6 as "Teaser"
    in Free. So all four lower-tier visuals get the teaser treatment.
    """
    components = payload["components"]
    tokens = load_tokens()

    out: dict[str, str] = {}

    # Tier-1: always full
    out["risk_dashboard"] = render_svg("risk_dashboard", components["risk_dashboard"])

    map_ctx = build_map_render_context(
        components["property_context_map"],
        address_lat=payload["address"]["lat"],
        address_lon=payload["address"]["lon"],
        basemap=None,  # offline-safe for unit-style E2E test
    )
    out["property_context_map"] = render_svg(
        "property_context_map", components["property_context_map"], map=map_ctx
    )

    # Tier-2 components
    ts_ctx = build_timeseries_render_context(components["velocity_timeseries"])
    ts_svg = render_svg("velocity_timeseries", components["velocity_timeseries"], chart=ts_ctx)

    soil_ctx = build_soil_stack_render_context(components["soil_context_stack"], tokens=tokens)
    soil_svg = render_svg("soil_context_stack", components["soil_context_stack"], stack=soil_ctx)

    radar_ctx = build_radar_render_context(components["correlation_radar"])
    radar_svg = render_svg("correlation_radar", components["correlation_radar"], radar=radar_ctx)

    hist_ctx = build_histogram_render_context(components["neighborhood_histogram"], tokens=tokens)
    hist_svg = render_svg("neighborhood_histogram", components["neighborhood_histogram"], hist=hist_ctx)

    if tier == "free":
        # Per SPEC §1 table: #3 (timeseries), #4 (soil), #5 (radar), #6 (histogram)
        # are all "Teaser" in Free.
        out["velocity_timeseries"] = wrap_teaser(ts_svg, cta_text="Vollbericht freischalten")
        out["soil_context_stack"] = wrap_teaser(soil_svg, cta_text="Vollbericht freischalten")
        out["correlation_radar"] = wrap_teaser(radar_svg, cta_text="Vollbericht freischalten")
        out["neighborhood_histogram"] = wrap_teaser(hist_svg, cta_text="Vollbericht freischalten")
    else:
        out["velocity_timeseries"] = ts_svg
        out["soil_context_stack"] = soil_svg
        out["correlation_radar"] = radar_svg
        out["neighborhood_histogram"] = hist_svg

    return out


def test_all_six_visuals_render_offline_premium() -> None:
    payload = _build_full_payload()
    visuals = _render_all_six(payload, tier="premium")
    assert set(visuals.keys()) == {
        "risk_dashboard", "property_context_map", "velocity_timeseries",
        "soil_context_stack", "correlation_radar", "neighborhood_histogram",
    }
    for name, svg in visuals.items():
        assert svg.startswith("<svg"), f"{name} missing outer <svg>"
        assert svg.endswith("</svg>") or svg.endswith("</svg>\n"), name


def test_all_six_visuals_render_offline_free_tier_with_teaser() -> None:
    payload = _build_full_payload()
    visuals = _render_all_six(payload, tier="free")
    # Tier-1 has no teaser
    assert "feGaussianBlur" not in visuals["risk_dashboard"]
    assert "feGaussianBlur" not in visuals["property_context_map"]
    # Tier-2 has teaser
    for tier2 in ("velocity_timeseries", "soil_context_stack",
                  "correlation_radar", "neighborhood_histogram"):
        assert "feGaussianBlur" in visuals[tier2], f"{tier2} missing blur filter"
        assert "Vollbericht freischalten" in visuals[tier2]


def _wrap_html(visuals: dict[str, str], title: str) -> str:
    sections_order = [
        ("risk_dashboard", "Komponente 1 · Risiko-Dashboard"),
        ("property_context_map", "Komponente 2 · Grundstück-im-Kontext"),
        ("velocity_timeseries", "Komponente 3 · Velocity-Zeitreihe"),
        ("soil_context_stack", "Komponente 4 · Bodenkontext-Stapel"),
        ("correlation_radar", "Komponente 5 · Korrelations-Spinne"),
        ("neighborhood_histogram", "Komponente 6 · Nachbarschafts-Vergleich"),
    ]
    sections = "\n".join(
        f'<section><h2>{label}</h2><div class="visual">{visuals[k]}</div></section>'
        for k, label in sections_order
    )
    return f"""<!doctype html>
<html><head>
  <meta charset="utf-8"><title>{title}</title>
  <style>
    @page {{ size: A4; margin: 14mm; }}
    body {{ margin: 0; font-family: -apple-system, sans-serif; }}
    h1 {{ font-size: 16pt; margin: 0 0 8pt; }}
    h2 {{ font-size: 11pt; color: #666; margin: 14pt 0 4pt; }}
    section {{ break-inside: avoid; margin-bottom: 6pt; }}
    .visual {{ width: 680px; max-width: 100%; }}
  </style>
</head><body>
  <h1>{title}</h1>
  {sections}
</body></html>"""


@pytest.mark.live
def test_v3_e2e_premium_pdf() -> None:
    from app.pdf_renderer import _find_chrome, html_to_pdf
    if _find_chrome() is None:
        pytest.skip("Chrome/Chromium not available")

    payload = _build_full_payload()
    visuals = _render_all_six(payload, tier="premium")
    html = _wrap_html(visuals, "GeoForensic Vollbericht — V.3 E2E (Premium)")
    pdf = html_to_pdf(html)
    assert pdf is not None
    assert pdf.startswith(b"%PDF-")
    # 6 SVGs + plenty of text → expect a substantial PDF
    assert len(pdf) > 30_000

    out_dir = Path(__file__).resolve().parent / "_artifacts"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "v3_premium.pdf").write_bytes(pdf)
    (out_dir / "v3_premium.html").write_text(html, encoding="utf-8")


@pytest.mark.live
def test_v3_e2e_free_teaser_pdf() -> None:
    from app.pdf_renderer import _find_chrome, html_to_pdf
    if _find_chrome() is None:
        pytest.skip("Chrome/Chromium not available")

    payload = _build_full_payload()
    visuals = _render_all_six(payload, tier="free")
    html = _wrap_html(visuals, "Bodenbericht Free — V.3 E2E (Teaser)")
    pdf = html_to_pdf(html)
    assert pdf is not None
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 30_000

    out_dir = Path(__file__).resolve().parent / "_artifacts"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "v3_free_teaser.pdf").write_bytes(pdf)
    (out_dir / "v3_free_teaser.html").write_text(html, encoding="utf-8")
