"""V.4.6 — Smoke tests for the polished Free teaser report."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.html_report import generate_html_report


def _example_kwargs() -> dict:
    return {
        "address": "Schulstraße 12, 76571 Gaggenau",
        "lat": 48.80123,
        "lon": 8.32456,
        "ampel": "gelb",
        "point_count": 47,
        "mean_velocity": -1.4,
        "max_velocity": -3.4,
        "geo_score": 72,
        "soil_profile": {
            "soilgrids": {
                "soc": 18, "phh2o": 64, "clay": 220, "sand": 510, "silt": 270, "bdod": 142,
            },
            "metals": {"Cd": 0.3, "Pb": 28, "Hg": 0.05, "As": 8, "Cr": 24, "Cu": 18, "Ni": 18, "Zn": 65},
            "metal_status": {"Cd": "ok", "Pb": "ok", "Hg": "ok", "As": "ok", "Cr": "ok", "Cu": "ok", "Ni": "ok", "Zn": "ok"},
            "nutrients": {"P": 28, "N": 1.7},
            "lucas_distance_km": 5.4,
        },
        "answers": {},
        "radius_m": 500,
        "egms_period_start": 2019,
        "egms_period_end": 2023,
        "operator_legal_name": "Tepnosholding GmbH",
        "operator_imprint_url": "https://bodenbericht.de/impressum.html",
    }


def test_teaser_renders_well_formed_html() -> None:
    html = generate_html_report(**_example_kwargs())
    assert html.startswith("<!doctype") or html.startswith("<!DOCTYPE")
    assert "</html>" in html


def test_trust_bar_appears_top_of_report() -> None:
    html = generate_html_report(**_example_kwargs())
    # Trust-Bar present
    assert 'class="trust-bar"' in html
    # Source badges
    for source in ("EGMS", "SoilGrids", "LUCAS", "BGR GÜK250", "DWD KOSTRA",
                   "BfG HWRM", "OpenStreetMap"):
        assert source in html, f"missing trust-bar source: {source}"
    # Trust-Bar sits BEFORE the locked-strap (i.e. on page 1, top)
    trust_idx = html.index('class="trust-bar"')
    locked_idx = html.index('class="section-label locked-strap"')
    assert trust_idx < locked_idx


def test_locked_strap_uses_accent_class() -> None:
    html = generate_html_report(**_example_kwargs())
    assert 'class="section-label locked-strap"' in html


def test_lock_pill_text_reads_freischalten() -> None:
    html = generate_html_report(**_example_kwargs())
    # New pill text drives conversion ("Vollbericht freischalten") instead
    # of just labelling the card ("Im Vollbericht enthalten")
    assert "Vollbericht freischalten" in html


def test_cta_visuals_strip_renders_six_tiles() -> None:
    html = generate_html_report(**_example_kwargs())
    assert 'class="cta-visuals"' in html
    # 6 vtile divs
    assert html.count('class="vtile"') == 6
    # Each tile has a label
    for label in ("Dashboard", "Karte", "Zeitreihe", "Boden­profil",
                  "Korrelation", "Histogramm"):
        assert label in html, f"missing CTA tile label: {label}"


def test_cta_copy_mentions_six_visualisations() -> None:
    html = generate_html_report(**_example_kwargs())
    # The new CTA copy explicitly references "sechs interaktive Visualisierungen"
    assert "Sechs interaktive Visualisierungen" in html


def test_no_undefined_references_in_html() -> None:
    """Sanity-check: no Jinja/format placeholders leaked through."""
    html = generate_html_report(**_example_kwargs())
    assert "{{" not in html
    assert "{%" not in html
    # f-string didn't fail to substitute (no literal "{" except inside SVGs)
    # — no obvious leftover braces around variable names
    import re
    # Look for {variable} patterns with a likely-Python name pattern
    leftover = re.findall(r'\{[a-z_][a-z_0-9]*\}', html, flags=re.IGNORECASE)
    # Some legit braces exist inside style/SVG content; filter to suspicious
    # python identifiers like {address}, {lat}, etc.
    suspicious = [t for t in leftover if t.lower() in {
        "{address}", "{lat}", "{lon}", "{ampel}", "{score}", "{point_count}",
        "{report_number}", "{logo_html}",
    }]
    assert not suspicious, f"unsubstituted f-string vars leaked: {suspicious}"


@pytest.mark.live
def test_v4_6_e2e_pdf_render() -> None:
    """Live: render the polished Free teaser to PDF and persist for review."""
    from app.pdf_renderer import _find_chrome, html_to_pdf
    if _find_chrome() is None:
        pytest.skip("Chrome/Chromium not available")

    html = generate_html_report(**_example_kwargs())
    pdf = html_to_pdf(html)
    assert pdf is not None
    assert pdf.startswith(b"%PDF-")
    # Free teaser had 1.86 MB before V.4.6; we add small assets only,
    # so it should stay roughly in that range. Loose check.
    assert len(pdf) < 3_000_000

    out_dir = Path(__file__).resolve().parent / "_artifacts"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "v4_6_free_polished.pdf").write_bytes(pdf)
    (out_dir / "v4_6_free_polished.html").write_text(html, encoding="utf-8")
