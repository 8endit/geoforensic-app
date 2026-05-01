"""V.1.2 — smoke tests for backend.app.visual_renderer.

Renders the hello-world template through the production code path and
asserts the produced SVG is well-formed and contains the expected
token values pulled from ``shared/visual_tokens.json``.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import pytest

from app.visual_renderer import (
    _ampel_band,
    _fmt_signed,
    load_tokens,
    render_svg,
)


def test_load_tokens_returns_expected_top_level_keys() -> None:
    tokens = load_tokens()
    for key in ("ampel", "structural", "typography", "layout", "report_design"):
        assert key in tokens, f"missing top-level key: {key}"


def test_ampel_band_classifies_velocity() -> None:
    assert _ampel_band(0.0)["label"] == "stabil"
    assert _ampel_band(-0.4)["label"] == "stabil"
    assert _ampel_band(-1.4)["label"] == "leicht"
    assert _ampel_band(-2.5)["label"] == "moderat"
    assert _ampel_band(4.0)["label"] == "auffällig"
    assert _ampel_band(6.5)["label"] == "erheblich"
    assert _ampel_band(20.0)["label"] == "kritisch"
    assert _ampel_band(None)["label"] == "stabil"


def test_fmt_signed_formats_correctly() -> None:
    assert _fmt_signed(0) == "0"
    assert _fmt_signed(1.4) == "+1.4"
    assert _fmt_signed(-1.4) == "-1.4"
    assert _fmt_signed(None) == "—"
    assert _fmt_signed(2.349, digits=2) == "+2.35"


def test_render_hello_world_produces_well_formed_svg() -> None:
    svg = render_svg("_hello_world", {
        "message": "Schulstraße 12, 76571 Gaggenau",
        "velocity": -1.4,
        "dark": False,
    })
    # Well-formed XML
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    # Tokens were resolved (leicht color = #5DCAA5 from spec §3)
    assert "#5DCAA5" in svg
    # Helper output present
    assert "+1.4" not in svg  # negative
    assert "-1.4 mm/Jahr" in svg
    assert "Schulstraße 12" in svg
    assert "Burland-Klasse 2" in svg
    assert "leicht" in svg


def test_render_with_kritisch_velocity_uses_kritisch_color() -> None:
    svg = render_svg("_hello_world", {
        "message": "Krisenadresse",
        "velocity": -25.0,
        "dark": True,
    })
    assert "#7A1F1F" in svg  # kritisch hex from tokens
    assert "kritisch" in svg


def test_render_missing_template_raises() -> None:
    with pytest.raises(Exception):
        render_svg("does_not_exist", {})


def test_viewbox_width_pulls_from_tokens() -> None:
    svg = render_svg("_hello_world", {"message": "x", "velocity": 0, "dark": False})
    match = re.search(r'viewBox="0 0 (\d+)', svg)
    assert match is not None
    assert int(match.group(1)) == 680  # spec §3 layout principle


def test_subset_fonts_under_size_budget() -> None:
    """V.1.4 acceptance: each subset woff2 < 40 KB."""
    from pathlib import Path
    fonts_dir = Path(__file__).resolve().parents[3] / "backend" / "static" / "fonts"
    woff2s = list(fonts_dir.glob("*.woff2"))
    assert len(woff2s) >= 4, f"Expected 4 subset fonts, got {len(woff2s)}: {woff2s}"
    for f in woff2s:
        size_kb = f.stat().st_size / 1024
        assert size_kb < 40, f"{f.name}: {size_kb:.1f} KB > 40 KB budget"


def test_tokens_css_generated_and_contains_ampel_vars() -> None:
    """V.1.3 acceptance: tokens.css generated from JSON contains all
    ampel custom properties."""
    from pathlib import Path
    css_path = (
        Path(__file__).resolve().parents[3]
        / "backend" / "static" / "css" / "tokens.css"
    )
    assert css_path.exists(), f"Run scripts/generate_tokens_css.py first ({css_path})"
    css = css_path.read_text(encoding="utf-8")
    for var in ("--ampel-stabil", "--ampel-leicht", "--ampel-kritisch",
                "--accent-own-property", "--font-display", "--font-mono"):
        assert var in css, f"Missing CSS var: {var}"
