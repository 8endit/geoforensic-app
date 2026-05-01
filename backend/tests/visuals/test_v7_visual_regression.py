"""V.7 — Visual-Regression-Tests for the six visual templates.

Pins the SVG output for three representative input scenarios so any
template/CSS change that drifts the rendering shows up as a diff.

Scenarios
---------
- *urban_dense*  — Berlin-style payload with full PSI density (47 points)
- *sparse*       — Schulstraße 12 Gaggenau (7 PSI points, sparse band)
- *no_data*      — empty payload, every component falls back to the
                   "—" / "Daten in Vorbereitung" rendering

Output
------
Each scenario × component combination is hashed (sha256 over the
rendered SVG bytes). The expected hashes live next to this file in
``_visual_regression_baselines.json``. To accept a deliberate change,
delete the JSON or invoke pytest with ``UPDATE_BASELINES=1`` env var.
"""

from __future__ import annotations

import hashlib
import json
import os
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
from app.visual_renderer import load_tokens, render_svg


REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_PAYLOAD = REPO_ROOT / "docs" / "visuals" / "example_payload.json"
BASELINE_FILE = Path(__file__).parent / "_visual_regression_baselines.json"


def _load_example() -> dict:
    return json.loads(EXAMPLE_PAYLOAD.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Scenario builders — pure inputs, deterministic outputs
# ---------------------------------------------------------------------------

def _scenario_urban_dense() -> dict:
    """Berlin-style address with 47 synthetic PSI points (dense urban
    coverage) and a steeper subsidence trend to differentiate from
    the sparse scenario."""
    ex = _load_example()
    components = ex["components"]
    lat_b, lon_b = 52.5142, 13.3145

    # 47 synthetic PSI points scattered around the Berlin centre with
    # mean velocity ~ -0.8 mm/yr (still stable urban) but max -2.5
    import random
    rnd = random.Random(42)  # deterministic
    psi: list[dict] = []
    for i in range(47):
        # Spread within ~250 m of centre (≈0.0025° lat, 0.0040° lon at 52.5°)
        dlat = rnd.uniform(-0.0025, 0.0025)
        dlon = rnd.uniform(-0.0040, 0.0040)
        v = rnd.gauss(-0.8, 0.7)
        # Small chance of a bigger outlier
        if rnd.random() < 0.05:
            v = rnd.uniform(-3.0, -2.0)
        psi.append({
            "lat": lat_b + dlat, "lon": lon_b + dlon,
            "velocity": round(v, 2),
            "coherence": round(rnd.uniform(0.7, 0.92), 2),
        })

    # Building footprint: 25 m × 18 m rectangle at the address
    deg_per_m_lat = 1.0 / 111_320.0
    import math
    deg_per_m_lon = 1.0 / (111_320.0 * math.cos(math.radians(lat_b)))
    half_w = 12.5 * deg_per_m_lon
    half_h = 9 * deg_per_m_lat
    poly = [
        [lon_b - half_w, lat_b - half_h],
        [lon_b + half_w, lat_b - half_h],
        [lon_b + half_w, lat_b + half_h],
        [lon_b - half_w, lat_b + half_h],
    ]

    # Slightly accelerated timeseries: same shape as Schulstraße but doubled
    base_ts = components["velocity_timeseries"]["psi_series"]
    accelerated = [{"date": p["date"],
                    "displacement_mm": round(p["displacement_mm"] * 1.4, 2)}
                   for p in base_ts]

    return build_payload(
        address={"full": "Bismarckstr. 10, 10625 Berlin", "lat": lat_b, "lon": lon_b},
        psi_points=psi,
        psi_timeseries=accelerated,
        precipitation_series=components["velocity_timeseries"]["precipitation_series"],
        annual_precipitation_mm=560,
        sealing_percent=72,
        clay_percent=18,
        slope_degrees=0.5,
        groundwater_depth_m=-2.4,
        soil_layers=components["soil_context_stack"]["layers"],
        building_footprint={
            "available": True, "polygon": poly,
            "centroid": [lon_b, lat_b],
        },
        radius_meters=500,
        tier="premium",
        report_id="GF-REG-URBAN",
    )


def _scenario_sparse() -> dict:
    """Schulstraße 12 Gaggenau — sparse PSI density."""
    ex = _load_example()
    components = ex["components"]
    return build_payload(
        address=ex["address"],
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
        report_id="GF-REG-SPARSE",
    )


def _scenario_no_data() -> dict:
    """Bare-minimum payload — every optional input is None."""
    return build_payload(
        address={"full": "No Data, 00000 Test", "lat": 50.0, "lon": 9.0},
        psi_points=[],
        psi_timeseries=[],
        radius_meters=500,
        tier="premium",
        report_id="GF-REG-NODATA",
    )


SCENARIOS = {
    "urban_dense": _scenario_urban_dense,
    "sparse": _scenario_sparse,
    "no_data": _scenario_no_data,
}


def _render_all(payload: dict) -> dict[str, str]:
    """Render the 6 components from a payload to SVG strings."""
    components = payload["components"]
    addr = payload["address"]
    tokens = load_tokens()

    rd = render_svg("risk_dashboard", components["risk_dashboard"])
    map_ctx = build_map_render_context(
        components["property_context_map"],
        address_lat=addr["lat"], address_lon=addr["lon"],
        basemap=None,  # baseline check is offline-safe; live tile fetch is non-deterministic
        tokens=tokens,
    )
    map_svg = render_svg("property_context_map",
                         components["property_context_map"], map=map_ctx)
    ts_ctx = build_timeseries_render_context(components["velocity_timeseries"])
    ts = render_svg("velocity_timeseries", components["velocity_timeseries"], chart=ts_ctx)
    soil_ctx = build_soil_stack_render_context(components["soil_context_stack"], tokens=tokens)
    soil = render_svg("soil_context_stack", components["soil_context_stack"], stack=soil_ctx)
    radar_ctx = build_radar_render_context(components["correlation_radar"])
    radar = render_svg("correlation_radar", components["correlation_radar"], radar=radar_ctx)
    hist_ctx = build_histogram_render_context(components["neighborhood_histogram"], tokens=tokens)
    hist = render_svg("neighborhood_histogram", components["neighborhood_histogram"], hist=hist_ctx)

    return {
        "risk_dashboard": rd,
        "property_context_map": map_svg,
        "velocity_timeseries": ts,
        "soil_context_stack": soil,
        "correlation_radar": radar,
        "neighborhood_histogram": hist,
    }


def _hash(svg: str) -> str:
    return hashlib.sha256(svg.encode("utf-8")).hexdigest()


def _render_all_hashes() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for scenario_name, builder in SCENARIOS.items():
        payload = builder()
        out[scenario_name] = {k: _hash(v) for k, v in _render_all(payload).items()}
    return out


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_visual_regression_baselines_match() -> None:
    """Every (scenario, component) hash must match the committed
    baseline. To regenerate after a deliberate change, run::

        UPDATE_BASELINES=1 pytest tests/visuals/test_v7_visual_regression.py -k baselines_match

    The freshly computed hashes are then written back to the baseline
    file in-place.
    """
    fresh = _render_all_hashes()

    if os.environ.get("UPDATE_BASELINES") == "1" or not BASELINE_FILE.exists():
        BASELINE_FILE.write_text(
            json.dumps(fresh, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if os.environ.get("UPDATE_BASELINES") == "1":
            pytest.skip("Baselines updated — re-run without UPDATE_BASELINES.")
        # First run ever: write and pass
        return

    expected = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    diffs: list[str] = []
    for scenario, comps in fresh.items():
        for comp, h in comps.items():
            exp = expected.get(scenario, {}).get(comp)
            if exp is None:
                diffs.append(f"new combo {scenario}/{comp}")
            elif exp != h:
                diffs.append(f"{scenario}/{comp}: expected {exp[:12]} got {h[:12]}")
    assert not diffs, (
        "Visual-Regression-Drift erkannt:\n  " + "\n  ".join(diffs)
        + "\nBeabsichtigt? UPDATE_BASELINES=1 pytest <this file> ausführen."
    )


def test_baselines_file_exists() -> None:
    """The baseline file must be committed alongside the tests."""
    assert BASELINE_FILE.exists(), (
        "Visual-Regression-Baselines fehlen. Erste Generation: "
        "UPDATE_BASELINES=1 pytest tests/visuals/test_v7_visual_regression.py"
    )


def test_no_data_scenario_renders_safely() -> None:
    """Every component must produce a well-formed SVG for the empty
    payload — sparse-data fallback is part of the contract (V.7)."""
    import xml.etree.ElementTree as ET
    payload = _scenario_no_data()
    svgs = _render_all(payload)
    for name, svg in svgs.items():
        root = ET.fromstring(svg)
        assert root.tag.endswith("svg"), f"{name}: malformed SVG"


def test_urban_and_sparse_produce_different_dashboards() -> None:
    """Sanity: different inputs must yield different dashboards."""
    urban = _render_all(_scenario_urban_dense())
    sparse = _render_all(_scenario_sparse())
    assert urban["risk_dashboard"] != sparse["risk_dashboard"]
    assert urban["property_context_map"] != sparse["property_context_map"]
