"""V.2.4 — tests for property_context_map.svg.jinja2 + render-context builder."""

from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from app.basemap import build_map_render_context
from app.visual_renderer import render_svg


REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_PAYLOAD = REPO_ROOT / "docs" / "visuals" / "example_payload.json"


@pytest.fixture(scope="module")
def example_payload() -> dict:
    return json.loads(EXAMPLE_PAYLOAD.read_text(encoding="utf-8"))


@pytest.fixture
def schulstrasse_component(example_payload: dict) -> dict:
    return example_payload["components"]["property_context_map"]


def test_render_context_without_basemap_synthesises_bbox(schulstrasse_component: dict) -> None:
    """No basemap → bbox synthesised around address; PSI points still
    project to inside the map area."""
    ctx = build_map_render_context(
        schulstrasse_component,
        address_lat=48.80123,
        address_lon=8.32456,
        basemap=None,
    )
    assert ctx["map_width"] == 600
    assert ctx["map_height"] == 320
    assert ctx["image_data_uri"] is None
    assert len(ctx["psi_dots"]) > 0
    # Address centroid sits inside the map area
    ax, ay = ctx["address_xy"]
    assert ctx["map_x"] <= ax <= ctx["map_x"] + ctx["map_width"]
    assert ctx["map_y"] <= ay <= ctx["map_y"] + ctx["map_height"]


def test_render_context_with_basemap_uses_provided_bbox() -> None:
    component = {
        "radius_meters": 500,
        "psi_points": [
            {"lat": 48.80123, "lon": 8.32456, "velocity": -1.4, "coherence": 0.8},
        ],
        "building_footprint": None,
    }
    fake_basemap = {
        "available": True,
        "image_data_uri": "data:image/png;base64,AAA",
        "bbox": (8.32, 48.80, 8.33, 48.81),
        "attribution": "© OpenStreetMap contributors © CARTO",
        "zoom": 16,
    }
    ctx = build_map_render_context(
        component,
        address_lat=48.80123,
        address_lon=8.32456,
        basemap=fake_basemap,
    )
    assert ctx["image_data_uri"] == "data:image/png;base64,AAA"
    assert ctx["attribution"].endswith("CARTO")
    assert ctx["zoom"] == 16
    assert len(ctx["psi_dots"]) == 1


def test_psi_dots_outside_window_are_dropped() -> None:
    """A PSI point far outside the bbox should be filtered out."""
    component = {
        "radius_meters": 500,
        "psi_points": [
            {"lat": 48.80123, "lon": 8.32456, "velocity": -1.4},  # in
            {"lat": 52.50, "lon": 13.40, "velocity": -0.5},        # Berlin, way outside
        ],
        "building_footprint": None,
    }
    ctx = build_map_render_context(component, 48.80123, 8.32456, basemap=None)
    assert len(ctx["psi_dots"]) == 1


def test_overlapping_dots_are_separated() -> None:
    """When two PSI points project to identical pixels, separation
    pushes them apart by at least ~8 px (Spec §4.2)."""
    component = {
        "radius_meters": 500,
        "psi_points": [
            {"lat": 48.80123, "lon": 8.32456, "velocity": -1.4},
            {"lat": 48.80123, "lon": 8.32456, "velocity": -2.0},
        ],
        "building_footprint": None,
    }
    ctx = build_map_render_context(component, 48.80123, 8.32456, basemap=None)
    a, b = ctx["psi_dots"]
    dist = math.hypot(a["cx"] - b["cx"], a["cy"] - b["cy"])
    assert dist >= 7.5  # minimum separation enforced


def test_velocity_color_uses_ampel(schulstrasse_component: dict) -> None:
    ctx = build_map_render_context(
        schulstrasse_component, 48.80123, 8.32456, basemap=None
    )
    # Schulstraße payload: -3.4 mm/yr → moderat (orange)
    moderat = "#EF9F27"
    auffaellig = "#E24B4A"
    colors = {d["color"] for d in ctx["psi_dots"]}
    assert moderat in colors or auffaellig in colors
    # And at least some stabil/leicht points
    assert "#1D9E75" in colors or "#5DCAA5" in colors


def test_render_template_produces_valid_svg(schulstrasse_component: dict) -> None:
    ctx = build_map_render_context(schulstrasse_component, 48.80123, 8.32456, basemap=None)
    svg = render_svg("property_context_map", schulstrasse_component, map=ctx)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert root.attrib["viewBox"].startswith("0 0 680 480")


def test_render_template_includes_psi_dots(schulstrasse_component: dict) -> None:
    ctx = build_map_render_context(schulstrasse_component, 48.80123, 8.32456, basemap=None)
    svg = render_svg("property_context_map", schulstrasse_component, map=ctx)
    # Expected: at least 5 ampel-coded circles in addition to legend dots
    circle_count = svg.count("<circle")
    assert circle_count >= len(ctx["psi_dots"]) + 5  # +6 legend dots roughly


def test_render_template_with_basemap_image() -> None:
    component = {
        "radius_meters": 500,
        "psi_points": [{"lat": 48.80123, "lon": 8.32456, "velocity": -1.4}],
        "building_footprint": None,
    }
    fake_basemap = {
        "available": True,
        "image_data_uri": "data:image/png;base64,iVBORw0KGgoAAAANS=",
        "bbox": (8.32, 48.80, 8.33, 48.81),
        "attribution": "© OpenStreetMap contributors © CARTO",
        "zoom": 16,
    }
    ctx = build_map_render_context(
        component, 48.80123, 8.32456, basemap=fake_basemap
    )
    svg = render_svg("property_context_map", component, map=ctx)
    # Image element with the data URI
    assert "data:image/png;base64,iVBORw0KGgoAAAANS=" in svg
    assert "© OpenStreetMap contributors © CARTO" in svg


def test_render_without_basemap_falls_back_to_grey() -> None:
    component = {
        "radius_meters": 500,
        "psi_points": [{"lat": 48.80123, "lon": 8.32456, "velocity": -1.4}],
        "building_footprint": None,
    }
    ctx = build_map_render_context(component, 48.80123, 8.32456, basemap=None)
    svg = render_svg("property_context_map", component, map=ctx)
    # Fallback rect with the structural bg color
    assert "#F1EFE8" in svg
    assert "<image" not in svg


def test_sparse_data_hint_when_under_10_psi() -> None:
    component = {
        "radius_meters": 500,
        "psi_points": [
            {"lat": 48.80123 + 0.001 * i, "lon": 8.32456, "velocity": -1.0}
            for i in range(5)
        ],
        "building_footprint": None,
    }
    ctx = build_map_render_context(component, 48.80123, 8.32456, basemap=None)
    svg = render_svg("property_context_map", component, map=ctx)
    assert "Sparse Data" in svg
    assert "5 PSI" in svg


def test_no_sparse_hint_when_over_10_psi(schulstrasse_component: dict) -> None:
    """Schulstraße payload has 7 points — should still show sparse hint
    by spec (<10 PSI)."""
    ctx = build_map_render_context(schulstrasse_component, 48.80123, 8.32456, basemap=None)
    svg = render_svg("property_context_map", schulstrasse_component, map=ctx)
    # 7 < 10 → sparse hint expected
    assert "Sparse Data" in svg


def test_building_polygon_path_renders(schulstrasse_component: dict) -> None:
    ctx = build_map_render_context(schulstrasse_component, 48.80123, 8.32456, basemap=None)
    svg = render_svg("property_context_map", schulstrasse_component, map=ctx)
    assert ctx["building_polygon_path"] is not None
    # Polygon path is rendered with "Ihr Gebäude" legend marker
    assert "Ihr Gebäude" in svg
    assert '<path d="M ' in svg


def test_legend_uses_token_colors(schulstrasse_component: dict) -> None:
    ctx = build_map_render_context(schulstrasse_component, 48.80123, 8.32456, basemap=None)
    svg = render_svg("property_context_map", schulstrasse_component, map=ctx)
    # All five ampel colors plus edge in the legend
    for hex_ in ("#1D9E75", "#5DCAA5", "#9FE1CB", "#EF9F27", "#E24B4A"):
        assert hex_ in svg


def test_north_arrow_present(schulstrasse_component: dict) -> None:
    ctx = build_map_render_context(schulstrasse_component, 48.80123, 8.32456, basemap=None)
    svg = render_svg("property_context_map", schulstrasse_component, map=ctx)
    assert "Norden" in svg
