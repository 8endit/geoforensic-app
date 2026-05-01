"""Smoke tests for backend.app.burland_classifier.

Acceptance criterion from VISUALS_ROLLOUT_PLAN V.0.1:
    Smoke-Test mit Beispielwerten aus example_payload.json ergibt
    class=2, label=leicht.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.burland_classifier import (
    BurlandResult,
    classify,
    compute_overall_grade,
    data_quality_from_psi_count,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_PAYLOAD = REPO_ROOT / "docs" / "visuals" / "example_payload.json"


@pytest.fixture(scope="module")
def example_payload() -> dict:
    return json.loads(EXAMPLE_PAYLOAD.read_text(encoding="utf-8"))


def test_acceptance_schulstrasse_12(example_payload: dict) -> None:
    """V.0.1 Akzeptanz: Schulstraße 12 → class=2, label=leicht."""
    dashboard = example_payload["components"]["risk_dashboard"]
    timeseries = example_payload["components"]["velocity_timeseries"]

    result = classify(
        mean_velocity_mm_per_year=dashboard["velocity_mm_per_year"],
        trend_slope_mm_per_year=timeseries["trend_slope_mm_per_year"],
        psi_count=dashboard["psi_count_in_radius"],
    )

    assert result is not None
    assert result.burland_class == 2
    assert result.label == "leicht"
    assert not result.trend_modifier_applied


def test_overall_grade_acceptance(example_payload: dict) -> None:
    """Schulstraße 12 has psi_count=47 (hoch) and class=2 → grade B."""
    dashboard = example_payload["components"]["risk_dashboard"]
    burland = classify(
        mean_velocity_mm_per_year=dashboard["velocity_mm_per_year"],
        psi_count=dashboard["psi_count_in_radius"],
    )
    grade = compute_overall_grade(burland, psi_count=dashboard["psi_count_in_radius"])
    assert grade.grade == "B"
    assert grade.data_quality == "hoch"


@pytest.mark.parametrize(
    "velocity, expected_class, expected_label",
    [
        (0.0, 1, "stabil"),
        (-0.3, 1, "stabil"),
        (0.5, 2, "leicht"),
        (-1.4, 2, "leicht"),
        (1.5, 3, "moderat"),
        (-2.7, 3, "moderat"),
        (3.0, 4, "auffällig"),
        (-4.2, 4, "auffällig"),
        (5.0, 5, "erheblich"),
        (-7.5, 5, "erheblich"),
        (10.0, 6, "kritisch"),
        (-15.0, 6, "kritisch"),
        (50.0, 6, "kritisch"),
    ],
)
def test_threshold_table(velocity: float, expected_class: int, expected_label: str) -> None:
    result = classify(mean_velocity_mm_per_year=velocity)
    assert result is not None
    assert result.burland_class == expected_class
    assert result.label == expected_label


def test_returns_none_on_missing_velocity() -> None:
    assert classify(mean_velocity_mm_per_year=None) is None


def test_trend_modifier_bumps_class() -> None:
    """If movement is accelerating, class is bumped by one."""
    # mean=1.0 (class 2 leicht), trend=2.0 — trend > 1.5x mean and ≥ 0.5 above
    result = classify(mean_velocity_mm_per_year=-1.0, trend_slope_mm_per_year=-2.0)
    assert result is not None
    assert result.burland_class == 3
    assert result.label == "moderat"
    assert result.trend_modifier_applied


def test_trend_does_not_bump_when_slope_close_to_mean() -> None:
    result = classify(mean_velocity_mm_per_year=-1.4, trend_slope_mm_per_year=-1.4)
    assert result is not None
    assert result.burland_class == 2
    assert not result.trend_modifier_applied


def test_max_velocity_bumps_when_far_above_mean() -> None:
    # mean=0.3 (class 1), max=4.0 (class 4) — max is 3 classes higher
    result = classify(mean_velocity_mm_per_year=-0.3, max_velocity_mm_per_year=-4.0)
    assert result is not None
    assert result.burland_class == 2  # bumped from 1 to 2 (capped at +1)


def test_data_quality_buckets() -> None:
    assert data_quality_from_psi_count(None) == "niedrig"
    assert data_quality_from_psi_count(0) == "niedrig"
    assert data_quality_from_psi_count(2) == "niedrig"
    assert data_quality_from_psi_count(3) == "begrenzt"
    assert data_quality_from_psi_count(9) == "begrenzt"
    assert data_quality_from_psi_count(10) == "mittel"
    assert data_quality_from_psi_count(29) == "mittel"
    assert data_quality_from_psi_count(30) == "hoch"
    assert data_quality_from_psi_count(150) == "hoch"


def test_overall_grade_with_thin_data_returns_dash() -> None:
    burland = classify(mean_velocity_mm_per_year=-0.2)
    grade = compute_overall_grade(burland, psi_count=1)
    assert grade.grade == "—"
    assert grade.data_quality == "niedrig"


def test_overall_grade_caps_at_b_with_begrenzt_quality() -> None:
    """Class 1 + 5 PSI points → grade B, never A."""
    burland = classify(mean_velocity_mm_per_year=-0.2, psi_count=5)
    assert burland.burland_class == 1
    grade = compute_overall_grade(burland, psi_count=5)
    assert grade.grade == "B"
    assert grade.data_quality == "begrenzt"


def test_overall_grade_class_5_or_6_is_e() -> None:
    burland_5 = BurlandResult(
        burland_class=5, label="erheblich", description="", velocity_basis="", trend_modifier_applied=False
    )
    burland_6 = BurlandResult(
        burland_class=6, label="kritisch", description="", velocity_basis="", trend_modifier_applied=False
    )
    assert compute_overall_grade(burland_5, psi_count=50).grade == "E"
    assert compute_overall_grade(burland_6, psi_count=50).grade == "E"
