"""Tests for backend.app.visual_payload — the data-contract assembler.

V.0.5 acceptance criterion: schema validation against
``docs/visuals/data_contract.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from app.visual_payload import build_payload


REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_PAYLOAD = REPO_ROOT / "docs" / "visuals" / "example_payload.json"
DATA_CONTRACT = REPO_ROOT / "docs" / "visuals" / "data_contract.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(DATA_CONTRACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def example_payload() -> dict:
    return json.loads(EXAMPLE_PAYLOAD.read_text(encoding="utf-8"))


@pytest.fixture
def schulstrasse_inputs(example_payload: dict) -> dict:
    """Build a build_payload kwargs dict from the example payload."""
    components = example_payload["components"]
    return {
        "address": example_payload["address"],
        "psi_points": components["property_context_map"]["psi_points"],
        "psi_timeseries": components["velocity_timeseries"]["psi_series"],
        "precipitation_series": components["velocity_timeseries"]["precipitation_series"],
        "annual_precipitation_mm": 835,
        "sealing_percent": components["soil_context_stack"]["sealing_percent"],
        "clay_percent": 22,
        "slope_degrees": 4.2,
        "groundwater_depth_m": components["soil_context_stack"]["groundwater_depth_m"],
        "soil_layers": components["soil_context_stack"]["layers"],
        "building_footprint": {
            "available": True,
            "polygon": components["property_context_map"]["building_footprint"]["polygon"],
            "centroid": components["property_context_map"]["building_footprint"]["centroid"],
        },
        "radius_meters": 500,
        "tier": "premium",
        "report_id": "GF-TEST-SCHULSTR",
        "data_sources_used": example_payload["metadata"]["data_sources_used"],
    }


def test_acceptance_payload_validates_against_schema(
    schema: dict, schulstrasse_inputs: dict
) -> None:
    """V.0.5 Akzeptanz: build_payload Output validiert gegen data_contract.json."""
    payload = build_payload(**schulstrasse_inputs)
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    assert not errors, "\n".join(
        f"{list(e.path)}: {e.message}" for e in errors
    )


def test_example_payload_itself_validates_against_schema(
    schema: dict, example_payload: dict
) -> None:
    """The Cozy-authored example must itself satisfy the (now-aligned) schema."""
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(example_payload), key=lambda e: e.path)
    assert not errors, "\n".join(
        f"{list(e.path)}: {e.message}" for e in errors
    )


def test_builds_required_top_level_fields(schulstrasse_inputs: dict) -> None:
    payload = build_payload(**schulstrasse_inputs)
    assert payload["report_id"] == "GF-TEST-SCHULSTR"
    assert payload["address"]["full"] == "Schulstraße 12, 76571 Gaggenau"
    assert payload["tier"] == "premium"
    assert "components" in payload
    assert "metadata" in payload


def test_burland_dashboard_uses_three_nearest_psi(schulstrasse_inputs: dict) -> None:
    """Dashboard velocity is mean of 3-nearest PSI to address.

    For the Schulstraße payload the 3 nearest PSI average -1.7 mm/yr
    (the example payload's hand-authored -1.4 was approximate). This
    yields Burland class 3 — defensible and within the same overall
    A-E band as the example's C/B.
    """
    payload = build_payload(**schulstrasse_inputs)
    rd = payload["components"]["risk_dashboard"]
    assert rd["burland_class"] in (2, 3)
    assert rd["burland_label"] in ("leicht", "moderat")
    assert rd["velocity_basis"] == "Mittel der drei nächsten PSI"
    assert rd["overall_grade"] in ("B", "C")
    assert -2.0 < rd["velocity_mm_per_year"] < -1.0


def test_radar_has_exactly_six_axes(schulstrasse_inputs: dict) -> None:
    payload = build_payload(**schulstrasse_inputs)
    axes = payload["components"]["correlation_radar"]["axes"]
    assert len(axes) == 6
    names = [a["name"] for a in axes]
    assert names == ["velocity", "precipitation", "sealing", "swelling_clay", "slope", "groundwater"]


def test_dominant_driver_is_set(schulstrasse_inputs: dict) -> None:
    payload = build_payload(**schulstrasse_inputs)
    radar = payload["components"]["correlation_radar"]
    assert radar["dominant_driver"] in {a["name"] for a in radar["axes"]}


def test_histogram_has_bins_and_percentile(schulstrasse_inputs: dict) -> None:
    payload = build_payload(**schulstrasse_inputs)
    hist = payload["components"]["neighborhood_histogram"]
    assert hist["psi_count"] == 7  # example payload has 7 PSI points
    assert "percentile" in hist
    assert hist["bins"]


def test_handles_missing_optional_data() -> None:
    """Bare-minimum inputs still produce a valid payload."""
    payload = build_payload(
        address={"full": "Test 1, 12345 Berlin", "lat": 52.52, "lon": 13.40},
        psi_points=[
            {"lat": 52.52, "lon": 13.40, "velocity": -0.3, "coherence": 0.8},
            {"lat": 52.521, "lon": 13.401, "velocity": -0.2, "coherence": 0.7},
            {"lat": 52.519, "lon": 13.399, "velocity": -0.4, "coherence": 0.85},
        ],
        psi_timeseries=[
            {"date": "2020-01-01", "displacement_mm": 0.0},
            {"date": "2021-01-01", "displacement_mm": -0.3},
            {"date": "2022-01-01", "displacement_mm": -0.6},
            {"date": "2023-01-01", "displacement_mm": -0.9},
        ],
    )
    rd = payload["components"]["risk_dashboard"]
    assert rd["burland_class"] == 1  # mean velocity -0.3 → stabil
    # Missing precipitation → no correlation_coefficient on velocity_timeseries
    assert "correlation_coefficient" not in payload["components"]["velocity_timeseries"]
    # Radar still has all 6 axes, with null where data missing
    radar = payload["components"]["correlation_radar"]
    assert len(radar["axes"]) == 6
    null_axes = [a["name"] for a in radar["axes"] if a["value"] is None]
    assert {"precipitation", "sealing", "swelling_clay", "slope", "groundwater"} <= set(null_axes)


def test_building_footprint_unavailable_renders_null() -> None:
    payload = build_payload(
        address={"full": "x", "lat": 52.0, "lon": 13.0},
        psi_points=[],
        psi_timeseries=[],
        building_footprint={"available": False, "note": "kein Treffer"},
    )
    assert payload["components"]["property_context_map"]["building_footprint"] is None


def test_default_report_id_is_generated_when_omitted() -> None:
    payload = build_payload(
        address={"full": "x", "lat": 0, "lon": 0},
        psi_points=[],
        psi_timeseries=[],
    )
    assert payload["report_id"].startswith("GF-")


def test_psi_points_with_coherence_preserve_field(schulstrasse_inputs: dict) -> None:
    payload = build_payload(**schulstrasse_inputs)
    points = payload["components"]["property_context_map"]["psi_points"]
    assert all("coherence" in p for p in points)


def test_correlation_coefficient_is_computed_when_both_series_present(
    schulstrasse_inputs: dict,
) -> None:
    payload = build_payload(**schulstrasse_inputs)
    ts = payload["components"]["velocity_timeseries"]
    assert "correlation_coefficient" in ts
    assert -1.0 <= ts["correlation_coefficient"] <= 1.0


def test_geology_label_is_picked_up_for_bedrock_layer() -> None:
    payload = build_payload(
        address={"full": "x", "lat": 48.8, "lon": 8.3},
        psi_points=[],
        psi_timeseries=[],
        geology={
            "available": True,
            "rock_type_short": "Buntsandstein",
            "stratigraphy": "Trias",
        },
    )
    layers = payload["components"]["soil_context_stack"]["layers"]
    bedrock = next(l for l in layers if l["type"] == "bedrock")
    assert bedrock["label"] == "Buntsandstein"
    assert "Trias" in bedrock["source"]
