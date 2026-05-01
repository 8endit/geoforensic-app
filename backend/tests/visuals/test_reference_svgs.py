"""V.1.6 — smoke tests for the 6 reference SVGs from docs/visuals/.

The reference SVGs are the design-source-of-truth provided by Cozy.
They will be ported to Jinja2 templates in V.2/V.3. Before that, this
suite verifies they:

1. Parse as well-formed XML/SVG (static check, no external deps).
2. Avoid SVG features known to misbehave in WeasyPrint or cairosvg
   (we no longer use cairosvg, but flagging here keeps options open).
3. Render successfully through ``pdf_renderer.html_to_pdf`` when
   embedded inline in HTML — the actual production render path
   (live test, marked ``live`` and skipped by default).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
REFERENCE_SVG_DIR = REPO_ROOT / "docs" / "visuals" / "reference_svgs"

EXPECTED_FILES = [
    "01_risk_dashboard.svg",
    "02_property_context_map.svg",
    "03_velocity_timeseries.svg",
    "04_soil_context_stack.svg",
    "05_correlation_radar.svg",
    "06_neighborhood_histogram.svg",
]

# SVG features known to need extra care across renderers. None are
# blockers in Chrome-Headless, but if a future SVG starts using one,
# the test fails so we have to think about WeasyPrint fallback.
FLAGGED_FEATURES = [
    "foreignObject",   # not in any pure-CSS renderer
    "feGaussianBlur",  # Chrome OK, WeasyPrint OK, cairosvg known issues
    "feColorMatrix",
    "feMorphology",
    "feTurbulence",
]


def _read_svg(name: str) -> str:
    path = REFERENCE_SVG_DIR / name
    assert path.exists(), f"Reference SVG missing: {path}"
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("filename", EXPECTED_FILES)
def test_reference_svg_exists_and_is_well_formed(filename: str) -> None:
    text = _read_svg(filename)
    root = ET.fromstring(text)
    assert root.tag.endswith("svg"), f"Root tag is not <svg> in {filename}"
    # Spec §3 layout: ViewBox-Breite 680px konsistent
    viewbox = root.attrib.get("viewBox", "")
    assert viewbox, f"{filename}: missing viewBox attribute"
    # ViewBox should start with 0 0 680 (some files may have whitespace, hence regex)
    assert re.match(r"\s*0\s+0\s+680\b", viewbox), (
        f"{filename}: viewBox '{viewbox}' is not 0 0 680 ... — Spec §3 says "
        "ViewBox-Breite konsistent 680 px"
    )


@pytest.mark.parametrize("filename", EXPECTED_FILES)
def test_reference_svg_does_not_use_flagged_features(filename: str) -> None:
    """Tracker for SVG features that may need special handling. The
    current set should produce zero hits — if a port to V.2/V.3 starts
    using one, this test fails and forces a deliberate decision."""
    text = _read_svg(filename)
    found = [f for f in FLAGGED_FEATURES if re.search(rf"<{f}\b", text)]
    assert not found, (
        f"{filename} uses flagged SVG features: {found}. "
        "Confirm Chrome + WeasyPrint render correctly before merging."
    )


def test_all_six_components_present() -> None:
    """Defensive: catch the case where a reference SVG goes missing."""
    actual = sorted(p.name for p in REFERENCE_SVG_DIR.glob("*.svg"))
    assert actual == sorted(EXPECTED_FILES), (
        f"reference_svgs/ contains {actual}, expected {EXPECTED_FILES}"
    )


# ---------------------------------------------------------------------------
# Live render test — wraps each reference SVG in HTML and pushes it
# through the production Chrome-Headless path. Skipped by default
# because Chrome subprocesses take a few seconds.
# ---------------------------------------------------------------------------

def _wrap_in_html(svg: str, title: str) -> str:
    return f"""<!doctype html>
<html><head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    @page {{ size: A4; margin: 12mm; }}
    body {{ margin: 0; font-family: -apple-system, sans-serif; }}
    h1 {{ font-size: 12pt; margin: 0 0 6pt; color: #444; }}
    .wrap {{ width: 680px; }}
  </style>
</head><body>
  <h1>Reference SVG · {title}</h1>
  <div class="wrap">{svg}</div>
</body></html>"""


@pytest.mark.live
@pytest.mark.parametrize("filename", EXPECTED_FILES)
def test_live_reference_svg_renders_through_pdf_renderer(filename: str) -> None:
    """V.1.6 acceptance: each reference SVG renders to PDF via
    Chrome-Headless without errors and produces a non-trivial PDF."""
    from app.pdf_renderer import _find_chrome, html_to_pdf

    if _find_chrome() is None:
        pytest.skip("Chrome/Chromium binary not found")

    svg = _read_svg(filename)
    html = _wrap_in_html(svg, filename)
    pdf_bytes = html_to_pdf(html)
    assert pdf_bytes is not None, f"{filename}: html_to_pdf returned None"
    assert pdf_bytes.startswith(b"%PDF-"), f"{filename}: not a valid PDF magic"
    assert len(pdf_bytes) > 1024, (
        f"{filename}: PDF is only {len(pdf_bytes)} bytes — likely empty"
    )


@pytest.mark.live
def test_live_chrome_renders_subset_fonts_without_substitution() -> None:
    """V.1.4 acceptance: HTML referencing the inline subset fonts
    renders without font-substitution failure (Chrome falls back to
    sans-serif silently if @font-face fails — we check by looking for
    a non-zero PDF size)."""
    from app.pdf_renderer import _find_chrome, html_to_pdf
    import base64

    if _find_chrome() is None:
        pytest.skip("Chrome/Chromium binary not found")

    fonts_dir = REPO_ROOT / "backend" / "static" / "fonts"
    sentient = (fonts_dir / "sentient-extralight.woff2").read_bytes()
    geist = (fonts_dir / "geist-mono-regular.woff2").read_bytes()
    s_b64 = base64.b64encode(sentient).decode("ascii")
    g_b64 = base64.b64encode(geist).decode("ascii")

    html = f"""<!doctype html>
<html><head>
  <meta charset="utf-8">
  <style>
    @font-face {{
      font-family: 'Sentient';
      src: url('data:font/woff2;base64,{s_b64}') format('woff2');
      font-weight: 200;
    }}
    @font-face {{
      font-family: 'Geist Mono';
      src: url('data:font/woff2;base64,{g_b64}') format('woff2');
      font-weight: 400;
    }}
    body {{ margin: 20mm; }}
    .display {{ font-family: 'Sentient'; font-size: 36pt; font-weight: 200; }}
    .mono    {{ font-family: 'Geist Mono'; font-size: 14pt; }}
  </style>
</head><body>
  <div class="display">GeoForensic Vollbericht</div>
  <div class="mono">Schulstraße 12 · 76571 Gaggenau · Bericht-Nr. GF-TEST</div>
  <div class="mono">Ampel-Test: stabil · leicht · moderat · auffällig · kritisch</div>
</body></html>"""

    pdf = html_to_pdf(html)
    assert pdf is not None
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 5_000  # inline fonts add real bytes
