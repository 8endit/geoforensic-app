"""V.2.2 — tests for risk_dashboard.svg.jinja2."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from app.visual_payload import build_payload
from app.visual_renderer import render_svg


REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_PAYLOAD = REPO_ROOT / "docs" / "visuals" / "example_payload.json"


@pytest.fixture(scope="module")
def example_payload() -> dict:
    return json.loads(EXAMPLE_PAYLOAD.read_text(encoding="utf-8"))


@pytest.fixture
def schulstrasse_payload(example_payload: dict) -> dict:
    components = example_payload["components"]
    return build_payload(
        address=example_payload["address"],
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
        report_id="GF-TEST",
    )


def test_renders_well_formed_svg(schulstrasse_payload: dict) -> None:
    svg = render_svg("risk_dashboard", schulstrasse_payload["components"]["risk_dashboard"])
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert root.attrib["viewBox"].startswith("0 0 680 260")


def test_contains_burland_class_and_label(schulstrasse_payload: dict) -> None:
    rd = schulstrasse_payload["components"]["risk_dashboard"]
    svg = render_svg("risk_dashboard", rd)
    # The class is rendered as a 64px number — should appear standalone
    assert f">{rd['burland_class']}<" in svg
    assert rd["burland_label"] in svg


def test_velocity_appears_with_signed_format(schulstrasse_payload: dict) -> None:
    svg = render_svg("risk_dashboard", schulstrasse_payload["components"]["risk_dashboard"])
    rd = schulstrasse_payload["components"]["risk_dashboard"]
    expected = f"{rd['velocity_mm_per_year']:+.1f} mm/Jahr"
    assert expected in svg


def test_grade_circle_uses_ampel_color() -> None:
    """For grade B (leicht), the circle color must be #5DCAA5 from tokens."""
    rd = {
        "burland_class": 2,
        "burland_label": "leicht",
        "burland_description": "±0,5–±1,5 mm/Jahr — saisonale Schwankung",
        "velocity_mm_per_year": -1.4,
        "velocity_basis": "Mittel der drei nächsten PSI",
        "trend": "stabil",
        "trend_description": "leichte saisonale Schwankung",
        "data_quality": "hoch",
        "data_quality_description": "47 PSI im 500 m-Radius",
        "psi_count_in_radius": 47,
        "overall_grade": "B",
        "overall_grade_label": "leichte Schwankung",
        "overall_grade_recommendation": "Routinebeobachtung",
    }
    svg = render_svg("risk_dashboard", rd)
    # Grade B → ampel.leicht.color
    assert "#5DCAA5" in svg


def test_grade_circle_uses_red_for_e() -> None:
    rd = {
        "burland_class": 5,
        "burland_label": "erheblich",
        "burland_description": "±5,0–±10,0 mm/Jahr",
        "velocity_mm_per_year": -7.0,
        "velocity_basis": "Mittel der drei nächsten PSI",
        "trend": "beschleunigend",
        "trend_description": "Setzungsrate deutlich über Rauschpegel",
        "data_quality": "hoch",
        "data_quality_description": "47 PSI",
        "psi_count_in_radius": 47,
        "overall_grade": "E",
        "overall_grade_label": "erheblich",
        "overall_grade_recommendation": "Dringend fachgutachterlich klären",
    }
    svg = render_svg("risk_dashboard", rd)
    assert "#A32D2D" in svg  # ampel.erheblich.color


def test_dash_grade_renders_without_error() -> None:
    """Sparse-data case: grade='—' must render with neutral color, not crash."""
    rd = {
        "burland_class": 1,
        "burland_label": "stabil",
        "burland_description": "Default",
        "velocity_mm_per_year": 0.0,
        "velocity_basis": "keine Daten",
        "trend": "uneindeutig",
        "trend_description": "Datenlage zu dünn",
        "data_quality": "niedrig",
        "data_quality_description": "0 PSI im 500 m-Radius",
        "psi_count_in_radius": 0,
        "overall_grade": "—",
        "overall_grade_label": "nicht bewertbar",
        "overall_grade_recommendation": "PSI-Datenlage zu dünn.",
    }
    svg = render_svg("risk_dashboard", rd)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    # Neutral fallback color (#888780) for dash grade
    assert "#888780" in svg


def test_psi_count_renders() -> None:
    rd = {
        "burland_class": 2,
        "burland_label": "leicht",
        "burland_description": "0–5 mm Setzung über 5 Jahre",
        "velocity_mm_per_year": -1.4,
        "velocity_basis": "Mittel der drei nächsten PSI",
        "trend": "stabil",
        "trend_description": "leichte saisonale Schwankung",
        "data_quality": "hoch",
        "data_quality_description": "Kohärenz 0.84",
        "psi_count_in_radius": 47,
        "overall_grade": "A",
        "overall_grade_label": "unauffällig",
        "overall_grade_recommendation": "Routinebeobachtung",
    }
    svg = render_svg("risk_dashboard", rd)
    assert ">47<" in svg


def test_no_undefined_references(schulstrasse_payload: dict) -> None:
    """StrictUndefined would have raised; sanity-check no Jinja
    placeholders leaked into the output."""
    svg = render_svg("risk_dashboard", schulstrasse_payload["components"]["risk_dashboard"])
    assert "{{" not in svg and "{%" not in svg


def test_reference_proportions_match() -> None:
    """Reference SVG layout: 3 rectangles at x={20, 215, 450} with
    widths 180/220/210. Catch unintended layout drift."""
    rd = {
        "burland_class": 2, "burland_label": "leicht",
        "burland_description": "—",
        "velocity_mm_per_year": -1.4, "velocity_basis": "x",
        "trend": "stabil", "trend_description": "x",
        "data_quality": "hoch", "data_quality_description": "x",
        "psi_count_in_radius": 47,
        "overall_grade": "A", "overall_grade_label": "x",
        "overall_grade_recommendation": "x",
    }
    svg = render_svg("risk_dashboard", rd)
    # Pull rect attributes (simple regex — three distinct x positions)
    xs = re.findall(r'<rect[^>]*\bx="(\d+)"[^>]*\brx="12"', svg)
    assert "20" in xs
    assert "450" in xs
