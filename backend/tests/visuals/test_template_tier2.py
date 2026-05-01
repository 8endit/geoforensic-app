"""V.3.1–V.3.5 — Tier-2 templates + teaser wrapper.

Tests cover the four component templates and the teaser-wrapper. Each
template is exercised with the Schulstraße-12 example payload so we
verify both the chart_helpers projection and the SVG output shape.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from app.chart_helpers import (
    build_histogram_render_context,
    build_radar_render_context,
    build_soil_stack_render_context,
    build_timeseries_render_context,
)
from app.visual_renderer import load_tokens, render_svg, wrap_teaser


REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_PAYLOAD = REPO_ROOT / "docs" / "visuals" / "example_payload.json"


@pytest.fixture(scope="module")
def example_payload() -> dict:
    return json.loads(EXAMPLE_PAYLOAD.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# V.3.1 velocity_timeseries
# ---------------------------------------------------------------------------

class TestVelocityTimeseries:
    def test_render_context_projects_psi_points(self, example_payload: dict) -> None:
        component = example_payload["components"]["velocity_timeseries"]
        ctx = build_timeseries_render_context(component)
        assert ctx["available"] is True
        assert len(ctx["psi_pts"]) == 10
        # All projected points sit inside the chart area
        for p in ctx["psi_pts"]:
            assert ctx["chart_x"] - 1 <= p["x_px"] <= ctx["chart_x"] + ctx["chart_width"] + 1
            assert ctx["chart_y"] - 1 <= p["y_px"] <= ctx["chart_y"] + ctx["chart_height"] + 1

    def test_zero_line_is_inside_chart(self, example_payload: dict) -> None:
        component = example_payload["components"]["velocity_timeseries"]
        ctx = build_timeseries_render_context(component)
        assert ctx["chart_y"] <= ctx["y_zero_px"] <= ctx["chart_y"] + ctx["chart_height"]

    def test_trend_line_present_when_slope_given(self, example_payload: dict) -> None:
        component = example_payload["components"]["velocity_timeseries"]
        ctx = build_timeseries_render_context(component)
        assert ctx["trend"] is not None
        # Trend slope from the example is -1.4 mm/yr
        assert ctx["trend"]["slope_mm_per_year"] == -1.4

    def test_rain_bars_match_precipitation_count(self, example_payload: dict) -> None:
        component = example_payload["components"]["velocity_timeseries"]
        ctx = build_timeseries_render_context(component)
        assert len(ctx["rain_bars"]) == 10

    def test_returns_unavailable_on_short_series(self) -> None:
        ctx = build_timeseries_render_context({
            "psi_series": [{"date": "2020-01-01", "displacement_mm": 0}],
        })
        assert ctx["available"] is False

    def test_render_template_well_formed(self, example_payload: dict) -> None:
        component = example_payload["components"]["velocity_timeseries"]
        ctx = build_timeseries_render_context(component)
        svg = render_svg("velocity_timeseries", component, chart=ctx)
        root = ET.fromstring(svg)
        assert root.tag.endswith("svg")
        assert root.attrib["viewBox"].startswith("0 0 680 320")
        assert "Bewegungsverlauf" in svg
        assert "Trend" in svg
        # Year labels rendered
        assert ">2020<" in svg
        assert ">2024<" in svg

    def test_correlation_in_footer_when_present(self, example_payload: dict) -> None:
        component = example_payload["components"]["velocity_timeseries"]
        ctx = build_timeseries_render_context(component)
        svg = render_svg("velocity_timeseries", component, chart=ctx)
        # correlation_coefficient = 0.71 in the example payload
        assert "Pearson r" in svg
        assert "0.71" in svg

    def test_no_data_panel_when_unavailable(self) -> None:
        component = {"psi_series": [], "precipitation_series": []}
        ctx = build_timeseries_render_context(component)
        svg = render_svg("velocity_timeseries", component, chart=ctx)
        assert "Keine Zeitreihe" in svg


# ---------------------------------------------------------------------------
# V.3.2 soil_context_stack
# ---------------------------------------------------------------------------

class TestSoilContextStack:
    def test_render_context_layers_proportional(self, example_payload: dict) -> None:
        component = example_payload["components"]["soil_context_stack"]
        ctx = build_soil_stack_render_context(component, tokens=load_tokens())
        assert ctx["available"] is True
        # Expect 4 layers (topsoil, subsoil, weathered, bedrock)
        assert len(ctx["layers"]) == 4
        # Total height equals the stack height
        total_h = sum(L["h"] for L in ctx["layers"])
        assert abs(total_h - ctx["stack_height"]) < 2.0

    def test_groundwater_y_inside_stack(self, example_payload: dict) -> None:
        component = example_payload["components"]["soil_context_stack"]
        ctx = build_soil_stack_render_context(component, tokens=load_tokens())
        assert ctx["groundwater_y"] is not None
        assert ctx["stack_y_top"] <= ctx["groundwater_y"] <= ctx["stack_y_top"] + ctx["stack_height"]

    def test_no_groundwater_renders_footer_hint(self) -> None:
        component = {
            "depth_m": 5,
            "has_building": True,
            "sealing_percent": 50,
            "layers": [
                {"type": "topsoil", "depth_top_m": 0, "depth_bottom_m": 0.3, "label": "Mutterboden"},
                {"type": "bedrock", "depth_top_m": 0.3, "depth_bottom_m": 5, "label": "Festgestein"},
            ],
            "groundwater_depth_m": None,
        }
        ctx = build_soil_stack_render_context(component, tokens=load_tokens())
        svg = render_svg("soil_context_stack", component, stack=ctx)
        assert "Grundwasser" not in svg or "Grundwasserstand nicht verfügbar" in svg

    def test_building_block_only_when_has_building(self) -> None:
        component_no_b = {
            "depth_m": 5,
            "has_building": False,
            "sealing_percent": None,
            "layers": [
                {"type": "topsoil", "depth_top_m": 0, "depth_bottom_m": 1, "label": "Boden"},
                {"type": "bedrock", "depth_top_m": 1, "depth_bottom_m": 5, "label": "Stein"},
            ],
        }
        ctx = build_soil_stack_render_context(component_no_b, tokens=load_tokens())
        assert ctx["has_building"] is False
        assert ctx["building_y"] is None
        svg = render_svg("soil_context_stack", component_no_b, stack=ctx)
        # No "OSM Footprint" label when no building
        assert "OSM Footprint" not in svg

    def test_render_template_well_formed(self, example_payload: dict) -> None:
        component = example_payload["components"]["soil_context_stack"]
        ctx = build_soil_stack_render_context(component, tokens=load_tokens())
        svg = render_svg("soil_context_stack", component, stack=ctx)
        root = ET.fromstring(svg)
        assert root.tag.endswith("svg")
        assert root.attrib["viewBox"].startswith("0 0 680 420")
        assert "Bodenprofil" in svg

    def test_layer_colors_match_tokens(self, example_payload: dict) -> None:
        component = example_payload["components"]["soil_context_stack"]
        ctx = build_soil_stack_render_context(component, tokens=load_tokens())
        svg = render_svg("soil_context_stack", component, stack=ctx)
        # Topsoil = #FAC775, subsoil = #EF9F27, bedrock = #444441
        assert "#FAC775" in svg
        assert "#EF9F27" in svg
        assert "#444441" in svg

    def test_depth_ticks_at_round_meter_marks(self, example_payload: dict) -> None:
        component = example_payload["components"]["soil_context_stack"]
        ctx = build_soil_stack_render_context(component, tokens=load_tokens())
        # 0, -1, -2, -3, -4, -5 m
        assert len(ctx["depth_ticks"]) == 6
        assert ctx["depth_ticks"][0]["label"] == "0 m"
        assert ctx["depth_ticks"][-1]["label"] == "−5 m"


# ---------------------------------------------------------------------------
# V.3.3 correlation_radar
# ---------------------------------------------------------------------------

class TestCorrelationRadar:
    def test_render_context_six_axes(self, example_payload: dict) -> None:
        component = example_payload["components"]["correlation_radar"]
        ctx = build_radar_render_context(component)
        assert ctx["available"] is True
        assert len(ctx["axes"]) == 6
        assert len(ctx["polygon_dots"]) == 6

    def test_polygon_built_from_six_points(self, example_payload: dict) -> None:
        component = example_payload["components"]["correlation_radar"]
        ctx = build_radar_render_context(component)
        assert ctx["polygon"] is not None
        # SVG points string has 6 comma-separated pairs
        coords = ctx["polygon"].split()
        assert len(coords) == 6

    def test_axis_with_null_value_renders_n_a(self) -> None:
        component = {
            "axes": [
                {"name": "velocity", "label": "Velocity", "value": 3.0, "raw_value": "−1.4 mm/J", "unit": "mm/Jahr"},
                {"name": "precipitation", "label": "Niederschlag", "value": None, "raw_value": "n/a", "unit": "mm/Jahr"},
                {"name": "sealing", "label": "Versiegelung", "value": 2.0, "raw_value": "40 %", "unit": "%"},
                {"name": "swelling_clay", "label": "Quelltonanteil", "value": 1.5, "raw_value": "lo", "unit": "Index"},
                {"name": "slope", "label": "Hangneigung", "value": 0.5, "raw_value": "1°", "unit": "°"},
                {"name": "groundwater", "label": "Grundwasser", "value": None, "raw_value": "n/a", "unit": "m"},
            ],
            "interpretation": "Test",
        }
        ctx = build_radar_render_context(component)
        # Polygon only includes non-null axes
        assert len(ctx["polygon_dots"]) == 4
        svg = render_svg("correlation_radar", component, radar=ctx)
        # Two "n/a" labels expected (one per missing axis)
        assert svg.count("n/a") >= 2

    def test_dominant_driver_label_highlighted(self, example_payload: dict) -> None:
        component = example_payload["components"]["correlation_radar"]
        ctx = build_radar_render_context(component)
        svg = render_svg("correlation_radar", component, radar=ctx)
        # Dominant driver name appears in interpretation footer
        assert ctx["dominant_driver"] == "precipitation"
        assert "Niederschlag" in svg or "precipitation" in svg

    def test_render_template_well_formed(self, example_payload: dict) -> None:
        component = example_payload["components"]["correlation_radar"]
        ctx = build_radar_render_context(component)
        svg = render_svg("correlation_radar", component, radar=ctx)
        root = ET.fromstring(svg)
        assert root.tag.endswith("svg")
        assert root.attrib["viewBox"].startswith("0 0 680 440")
        # Axis labels rendered
        for label in ("Velocity", "Niederschlag", "Versiegelung",
                      "Quelltonanteil", "Hangneigung", "Grundwasser"):
            assert label in svg

    def test_axis_values_in_0_5_range(self, example_payload: dict) -> None:
        component = example_payload["components"]["correlation_radar"]
        ctx = build_radar_render_context(component)
        # All polygon dots inside the radius_max disc
        for d in ctx["polygon_dots"]:
            from math import hypot
            r = hypot(d["cx"] - ctx["cx"], d["cy"] - ctx["cy"])
            assert r <= ctx["radius_max"] + 1e-3


# ---------------------------------------------------------------------------
# V.3.4 neighborhood_histogram
# ---------------------------------------------------------------------------

class TestNeighborhoodHistogram:
    def test_render_context_bars_and_marker(self, example_payload: dict) -> None:
        component = example_payload["components"]["neighborhood_histogram"]
        ctx = build_histogram_render_context(component, tokens=load_tokens())
        assert ctx["available"] is True
        # 9 bins in example payload (after dropping empty ones, all are populated)
        assert len(ctx["bars"]) == 9
        # Own velocity marker at -1.4 → x somewhere in chart
        assert ctx["own_x"] is not None

    def test_bar_colors_use_ampel(self, example_payload: dict) -> None:
        component = example_payload["components"]["neighborhood_histogram"]
        ctx = build_histogram_render_context(component, tokens=load_tokens())
        svg = render_svg("neighborhood_histogram", component, hist=ctx)
        # Stable bands present
        assert "#1D9E75" in svg  # stabil

    def test_dashed_marker_line_for_own_property(self, example_payload: dict) -> None:
        component = example_payload["components"]["neighborhood_histogram"]
        ctx = build_histogram_render_context(component, tokens=load_tokens())
        svg = render_svg("neighborhood_histogram", component, hist=ctx)
        # Dashed line color = accent-own-property
        assert "stroke-dasharray=\"4 3\"" in svg
        assert "#185FA5" in svg
        assert "Ihr Grundstück" in svg

    def test_own_value_label_rendered_with_signed_format(self, example_payload: dict) -> None:
        component = example_payload["components"]["neighborhood_histogram"]
        ctx = build_histogram_render_context(component, tokens=load_tokens())
        svg = render_svg("neighborhood_histogram", component, hist=ctx)
        # own_velocity = -1.4 → signed format "-1.4"
        assert "-1.4" in svg

    def test_psi_count_in_footer(self, example_payload: dict) -> None:
        component = example_payload["components"]["neighborhood_histogram"]
        ctx = build_histogram_render_context(component, tokens=load_tokens())
        svg = render_svg("neighborhood_histogram", component, hist=ctx)
        # Example psi_count = 47
        assert "47 PSI" in svg

    def test_render_template_well_formed(self, example_payload: dict) -> None:
        component = example_payload["components"]["neighborhood_histogram"]
        ctx = build_histogram_render_context(component, tokens=load_tokens())
        svg = render_svg("neighborhood_histogram", component, hist=ctx)
        root = ET.fromstring(svg)
        assert root.tag.endswith("svg")
        assert root.attrib["viewBox"].startswith("0 0 680 280")

    def test_sparse_hint_when_under_20(self) -> None:
        component = {
            "bins": [{"min": -1, "max": 0, "count": 3}, {"min": 0, "max": 1, "count": 5}],
            "own_velocity": -0.3,
            "psi_count": 8,
            "interpretation": "Im stabilen Bereich",
        }
        ctx = build_histogram_render_context(component, tokens=load_tokens())
        svg = render_svg("neighborhood_histogram", component, hist=ctx)
        assert "Stichprobe klein" in svg
        assert "8 PSI" in svg


# ---------------------------------------------------------------------------
# V.3.5 _teaser_wrapper
# ---------------------------------------------------------------------------

class TestTeaserWrapper:
    def test_wrap_teaser_extracts_dimensions(self, example_payload: dict) -> None:
        # Render a Tier-2 template, wrap it, verify wrapper SVG dimensions
        component = example_payload["components"]["correlation_radar"]
        ctx = build_radar_render_context(component)
        inner = render_svg("correlation_radar", component, radar=ctx)
        wrapped = wrap_teaser(inner, cta_text="Premium-Inhalt")
        m = re.search(r'<svg[^>]*viewBox="0 0 (\d+) (\d+)"', wrapped)
        assert m is not None
        assert m.group(1) == "680"
        assert m.group(2) == "440"

    def test_wrap_teaser_contains_blur_filter(self, example_payload: dict) -> None:
        component = example_payload["components"]["correlation_radar"]
        ctx = build_radar_render_context(component)
        inner = render_svg("correlation_radar", component, radar=ctx)
        wrapped = wrap_teaser(inner)
        assert "feGaussianBlur" in wrapped
        assert 'filter="url(#teaser-blur)"' in wrapped

    def test_wrap_teaser_contains_lock_icon_and_cta(self, example_payload: dict) -> None:
        component = example_payload["components"]["correlation_radar"]
        ctx = build_radar_render_context(component)
        inner = render_svg("correlation_radar", component, radar=ctx)
        wrapped = wrap_teaser(inner, cta_text="Bericht freischalten",
                              cta_url="https://geoforensic.de/upgrade")
        # Lock body rect (rx=4) + bügel path
        assert 'rx="4"' in wrapped
        assert "Bericht freischalten" in wrapped
        assert "https://geoforensic.de/upgrade" in wrapped

    def test_wrap_teaser_inner_svg_is_inlined(self, example_payload: dict) -> None:
        component = example_payload["components"]["correlation_radar"]
        ctx = build_radar_render_context(component)
        inner = render_svg("correlation_radar", component, radar=ctx)
        wrapped = wrap_teaser(inner)
        # Inner content (axis labels) should still be present
        assert "Niederschlag" in wrapped
        assert "Quelltonanteil" in wrapped
        # Wrapper has its own outer <svg>, plus the inner <svg> nested
        assert wrapped.count("<svg") >= 2

    def test_wrap_teaser_works_for_all_four_tier2_components(self, example_payload: dict) -> None:
        components = example_payload["components"]
        # velocity_timeseries
        ctx_t = build_timeseries_render_context(components["velocity_timeseries"])
        inner_t = render_svg("velocity_timeseries", components["velocity_timeseries"], chart=ctx_t)
        wrapped_t = wrap_teaser(inner_t, cta_text="Vollbericht freischalten")
        assert "feGaussianBlur" in wrapped_t

        # soil_context_stack
        ctx_s = build_soil_stack_render_context(components["soil_context_stack"], tokens=load_tokens())
        inner_s = render_svg("soil_context_stack", components["soil_context_stack"], stack=ctx_s)
        wrapped_s = wrap_teaser(inner_s)
        assert "feGaussianBlur" in wrapped_s

        # correlation_radar
        ctx_r = build_radar_render_context(components["correlation_radar"])
        inner_r = render_svg("correlation_radar", components["correlation_radar"], radar=ctx_r)
        wrapped_r = wrap_teaser(inner_r)
        assert "feGaussianBlur" in wrapped_r

        # neighborhood_histogram
        ctx_h = build_histogram_render_context(
            components["neighborhood_histogram"], tokens=load_tokens()
        )
        inner_h = render_svg("neighborhood_histogram", components["neighborhood_histogram"], hist=ctx_h)
        wrapped_h = wrap_teaser(inner_h)
        assert "feGaussianBlur" in wrapped_h
