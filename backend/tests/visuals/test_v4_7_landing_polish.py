"""V.4.7 — smoke tests for the landing-page redesign.

The standalone #visuals section was removed 2026-05-01 and the six
visuals are now woven into Hero, Problem-Sektion, How-It-Works,
Benefits and Premium-Teaser. Tests verify each visual is referenced
in its narrative section.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
LANDING_INDEX = REPO_ROOT / "landing" / "index.html"
LANDING_VISUALS = REPO_ROOT / "landing" / "static" / "visuals"


# ---------------------------------------------------------------------------
# Pre-rendered SVG file integrity
# ---------------------------------------------------------------------------

def test_six_static_visuals_exist() -> None:
    expected = {
        "01_risk_dashboard.svg",
        "02_property_context_map.svg",
        "03_velocity_timeseries.svg",
        "04_soil_context_stack.svg",
        "05_correlation_radar.svg",
        "06_neighborhood_histogram.svg",
    }
    actual = {p.name for p in LANDING_VISUALS.glob("*.svg")}
    missing = expected - actual
    assert not missing, f"missing pre-rendered visuals: {missing}"


def test_each_pre_rendered_visual_is_valid_svg() -> None:
    for path in LANDING_VISUALS.glob("*.svg"):
        text = path.read_text(encoding="utf-8")
        root = ET.fromstring(text)
        assert root.tag.endswith("svg"), f"{path.name}: root tag is {root.tag}"
        viewbox = root.attrib.get("viewBox", "")
        assert "680" in viewbox, f"{path.name}: viewBox '{viewbox}' missing 680"


def test_pre_rendered_visuals_under_size_budget() -> None:
    """Most visuals are pure SVG and stay tiny; the property-context-map
    embeds a CartoDB basemap composite as a base64 PNG so its budget is
    higher (allowed: 250 KB to fit a 600x320 PNG at z=16)."""
    for path in LANDING_VISUALS.glob("*.svg"):
        size_kb = path.stat().st_size / 1024
        budget = 250 if "property_context_map" in path.name else 12
        assert size_kb < budget, (
            f"{path.name}: {size_kb:.1f} KB exceeds {budget} KB budget"
        )


def test_property_context_map_has_real_basemap() -> None:
    """Landing demo must show a real CartoDB tile composite, not the
    grey fallback. Verified by presence of an inline PNG data URI."""
    text = (LANDING_VISUALS / "02_property_context_map.svg").read_text(encoding="utf-8")
    assert "data:image/png;base64," in text, (
        "Karten-Visual enthält kein eingebettetes Basemap-PNG — "
        "build_landing_visuals.py mit Live-Tile-Fetch erneut laufen lassen."
    )
    # CartoDB attribution rendered in the footer
    assert "CARTO" in text


# ---------------------------------------------------------------------------
# Standalone showcase removed
# ---------------------------------------------------------------------------

def test_standalone_visual_showcase_section_is_gone() -> None:
    """The 2026-04-30 #visuals gallery section was removed in favour of
    narrative integration."""
    html = LANDING_INDEX.read_text(encoding="utf-8")
    assert 'id="visuals"' not in html, (
        "Standalone #visuals section should have been removed"
    )
    assert "Sechs Visualisierungen, die zeigen" not in html


# ---------------------------------------------------------------------------
# Visual placement: each SVG appears in its narrative section
# ---------------------------------------------------------------------------

def _section(html: str, marker: str, end_marker: str) -> str:
    """Return the substring between two `<!-- xxx -->` markers."""
    start = html.index(marker)
    end = html.index(end_marker, start)
    return html[start:end]


def test_hero_contains_risk_dashboard() -> None:
    """Hero gets the headline-card visual: Risiko-Dashboard right of
    the lead form."""
    html = LANDING_INDEX.read_text(encoding="utf-8")
    hero = _section(html, "<!-- HERO SECTION", "<!-- TRUST BAR")
    assert "01_risk_dashboard.svg" in hero
    # Two-column hero now wraps copy + visual
    assert "lg:grid-cols-2" in hero


def test_problem_section_pairs_three_pains_with_visuals() -> None:
    html = LANDING_INDEX.read_text(encoding="utf-8")
    pain = _section(html, "<!-- PROBLEM / PAIN SECTION",
                    "<!-- TODO: Eigene Sub-Landingpages")
    # Pain 1 (Altlasten) ↔ Bodenkontext-Stapel
    assert "04_soil_context_stack.svg" in pain
    assert "Sie sehen nicht, was unter der Erde liegt." in pain
    # Pain 2 (Setzungen) ↔ Velocity-Zeitreihe
    assert "03_velocity_timeseries.svg" in pain
    assert "Saisonal oder strukturell?" in pain
    # Pain 3 (Nachbarschaft) ↔ Histogramm
    assert "06_neighborhood_histogram.svg" in pain
    assert "Wo stehen Sie im Vergleich" in pain
    # Each pain row is a 2-column grid
    pain_rows = re.findall(
        r'class="grid lg:grid-cols-2 gap-10 lg:gap-16 items-center', pain
    )
    assert len(pain_rows) == 3, f"expected 3 pain rows, got {len(pain_rows)}"


def test_problem_alternates_visual_left_and_right() -> None:
    """Pain 2 (middle row) reverses order: copy on the right
    (lg:order-2), visual on the left (lg:order-1)."""
    html = LANDING_INDEX.read_text(encoding="utf-8")
    pain = _section(html, "<!-- PROBLEM / PAIN SECTION",
                    "<!-- TODO: Eigene Sub-Landingpages")
    assert "lg:order-1" in pain and "lg:order-2" in pain


def test_how_it_works_step2_has_property_context_map() -> None:
    html = LANDING_INDEX.read_text(encoding="utf-8")
    how = _section(html, "<!-- HOW IT WORKS", "<!-- BENEFITS / FEATURES")
    assert "02_property_context_map.svg" in how
    assert "Schritt 2 — was die Pipeline produziert" in how


def test_benefits_uses_correlation_radar() -> None:
    html = LANDING_INDEX.read_text(encoding="utf-8")
    ben = _section(html, "<!-- BENEFITS / FEATURES",
                   "<!-- TESTIMONIALS / SOCIAL PROOF")
    # Old mock-result block (Bodenbewegung / Schwermetalle bars) is gone
    assert 'class="w-full bg-gray-100 rounded-full h-2"' not in ben
    # New: Korrelations-Spinne
    assert "05_correlation_radar.svg" in ben
    assert "Sechs Risikotreiber auf einen Blick" in ben


def test_premium_teaser_lists_additional_data_layers() -> None:
    """The 6-tile mini-grid was removed 2026-05-01 (oversharing — the
    visuals are already shown in Hero/Problem/HowItWorks/Benefits).
    What stays: the bullet list of additional data layers and the
    waitlist form."""
    html = LANDING_INDEX.read_text(encoding="utf-8")
    prem = _section(html, "<!-- PREMIUM TEASER", "<!-- FOOTER")
    # The mini-grid headline + thumbnails are gone
    assert "Sechs Visualisierungen freischalten" not in prem
    for f in (
        "01_risk_dashboard.svg", "02_property_context_map.svg",
        "03_velocity_timeseries.svg", "04_soil_context_stack.svg",
        "05_correlation_radar.svg", "06_neighborhood_histogram.svg",
    ):
        assert f"/static/visuals/{f}" not in prem, (
            f"premium-teaser still references {f} — should have been removed"
        )
    # The data-layer list survives
    assert "Was der Vollbericht zusätzlich auswertet" in prem
    assert "Altlasten-Verdachtsflächen" in prem
    assert "Hochwasser-Gefahrenzonen" in prem


def test_trust_bar_lists_actual_sources() -> None:
    """Trust-Bar redesign from V.4.7 stays — pills with real source
    names, plus a DSGVO note linking to /datenquellen.html."""
    html = LANDING_INDEX.read_text(encoding="utf-8")
    for source in (
        "Copernicus EGMS", "SoilGrids 250 m", "LUCAS Topsoil",
        "BGR GÜK250", "DWD KOSTRA", "BfG HWRM", "EU 2025/2360",
    ):
        assert source in html, f"missing trust-bar source: {source}"


# ---------------------------------------------------------------------------
# Cross-section visual count + a11y
# ---------------------------------------------------------------------------

def test_visuals_referenced_exactly_at_expected_count() -> None:
    """Each of 6 visuals appears in exactly one narrative section
    (Premium-Teaser-Mini-Grid removed 2026-05-01):
    Hero(1) + Problem(3) + How-It-Works(1) + Benefits(1) = 6 refs."""
    html = LANDING_INDEX.read_text(encoding="utf-8")
    refs = re.findall(r'src="/static/visuals/(\d{2})_[^"]+\.svg"', html)
    assert len(refs) == 6, f"expected 6 visual refs, got {len(refs)}: {refs}"
    # All 6 distinct visuals are referenced
    assert set(refs) == {"01", "02", "03", "04", "05", "06"}


def test_each_visual_image_has_alt_text() -> None:
    """A11y: every <img> referencing a static visual carries an
    alt-attribute."""
    html = LANDING_INDEX.read_text(encoding="utf-8")
    imgs = re.findall(r'<img\b[^>]*src="/static/visuals/[^"]+\.svg"[^>]*>', html)
    assert imgs, "no visual <img> tags found"
    for tag in imgs:
        assert "alt=" in tag, f"<img> missing alt: {tag[:100]}"


def test_landing_html_basic_xml_balance() -> None:
    """Lightweight sanity: the new sections balance their grid wrappers."""
    html = LANDING_INDEX.read_text(encoding="utf-8")
    # Count <section> opens vs closes — must match
    opens = len(re.findall(r"<section\b", html))
    closes = len(re.findall(r"</section>", html))
    assert opens == closes, f"unbalanced sections: {opens} open, {closes} close"


# ---------------------------------------------------------------------------
# Live render through Chrome — regression check that page builds
# ---------------------------------------------------------------------------

@pytest.mark.live
def test_v4_7_e2e_landing_renders_via_chrome_with_visuals() -> None:
    """Render landing/index.html through Chrome-Headless and verify
    the resulting PDF includes the visuals."""
    from app.pdf_renderer import _find_chrome
    import os
    import subprocess
    import tempfile

    chrome = _find_chrome()
    if chrome is None:
        pytest.skip("Chrome/Chromium not available")

    html_text = LANDING_INDEX.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        dest_index = tmp_path / "index.html"
        dest_index.write_text(html_text, encoding="utf-8")
        dest_static = tmp_path / "static" / "visuals"
        dest_static.mkdir(parents=True, exist_ok=True)
        for svg in LANDING_VISUALS.glob("*.svg"):
            (dest_static / svg.name).write_bytes(svg.read_bytes())
        # Provide a stub tailwind.css so Chrome doesn't 404 (the rendered
        # PDF doesn't need exact styling — we're just checking that the
        # six visuals embed cleanly)
        (tmp_path / "tailwind.css").write_text(
            (REPO_ROOT / "landing" / "tailwind.css").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        out_pdf = tmp_path / "landing.pdf"
        cmd = [
            chrome, "--headless", "--disable-gpu", "--no-sandbox",
            "--disable-software-rasterizer", "--disable-dev-shm-usage",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=6000",
            "--print-to-pdf=" + str(out_pdf),
            "--no-pdf-header-footer",
            "file:///" + str(dest_index).replace("\\", "/"),
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=90)
        assert out_pdf.exists(), (
            f"chrome failed to produce PDF: rc={result.returncode}, "
            f"stderr={result.stderr.decode('utf-8', errors='replace')[:300]}"
        )
        pdf_bytes = out_pdf.read_bytes()
        assert pdf_bytes.startswith(b"%PDF-")
        assert len(pdf_bytes) > 100_000

        out_dir = Path(__file__).resolve().parent / "_artifacts"
        out_dir.mkdir(exist_ok=True)
        (out_dir / "v4_7_landing_redesigned.pdf").write_bytes(pdf_bytes)
