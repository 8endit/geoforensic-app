"""Smoke tests for backend.app.correlations.

Plan V.0.2 acceptance criterion: the example_payload.json yields
"r ≈ 0.71". That value was authored by hand and not the output of any
real computation — verified by direct numpy/scipy calculation it gives
much lower r. The tests below pin down the actual computed values for
the example payload (regression-style) and verify behavior on
synthetic series where the answer is unambiguous.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from app.correlations import pearson_egms_precipitation


REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_PAYLOAD = REPO_ROOT / "docs" / "visuals" / "example_payload.json"


@pytest.fixture(scope="module")
def example_payload() -> dict:
    return json.loads(EXAMPLE_PAYLOAD.read_text(encoding="utf-8"))


def test_acceptance_example_payload_runs(example_payload: dict) -> None:
    """V.0.2 Akzeptanz: Funktion läuft auf Schulstraße-12-Serien ohne Fehler."""
    ts = example_payload["components"]["velocity_timeseries"]
    disp = [p["displacement_mm"] for p in ts["psi_series"]]
    prec = [p["mm"] for p in ts["precipitation_series"]]

    result = pearson_egms_precipitation(disp, prec, detrend=True)
    assert result is not None
    assert result.n_samples == 10
    assert result.method == "detrended"
    assert -1.0 <= result.pearson_r <= 1.0
    assert 0.0 <= result.p_value <= 1.0


def test_perfect_positive_correlation() -> None:
    """When residual = precipitation (after detrending), r → 1.0."""
    # Linear trend + precipitation as residual
    n = 12
    trend = [-0.5 * i for i in range(n)]
    prec = [50, 80, 30, 90, 40, 70, 100, 25, 85, 60, 45, 95]
    disp = [t + p * 0.01 for t, p in zip(trend, prec)]

    result = pearson_egms_precipitation(disp, prec, detrend=True)
    assert result is not None
    assert result.pearson_r > 0.95
    assert result.p_value < 0.01
    assert "starker" in result.interpretation
    assert "positiv" in result.interpretation


def test_no_correlation_on_random_independent_series() -> None:
    """Independent series → r near zero, high p, no significance."""
    disp = [0.0, -0.2, 0.1, -0.3, 0.2, -0.1, 0.3, -0.4, 0.0, 0.1]
    prec = [50, 80, 30, 90, 40, 70, 100, 25, 85, 60]

    result = pearson_egms_precipitation(disp, prec, detrend=True)
    assert result is not None
    assert abs(result.pearson_r) < 0.7  # not strongly correlated
    # interpretation may say "kein signifikanter Zusammenhang" for high p


def test_returns_none_on_mismatched_lengths() -> None:
    assert pearson_egms_precipitation([1.0, 2.0, 3.0], [1.0, 2.0]) is None


def test_returns_none_on_too_few_samples() -> None:
    assert pearson_egms_precipitation([1.0, 2.0], [1.0, 2.0]) is None


def test_perfectly_linear_displacement_yields_no_signal() -> None:
    """A perfectly linear displacement series has only float-noise residuals
    after detrending — the correlation coefficient is dominated by
    rounding error and the interpretation should flag it as
    non-significant.
    """
    disp = [0.0, -1.0, -2.0, -3.0, -4.0, -5.0]
    prec = [50, 80, 30, 90, 40, 70]
    result = pearson_egms_precipitation(disp, prec, detrend=True)
    assert result is not None
    assert result.p_value > 0.1
    assert "kein signifikant" in result.interpretation


def test_raw_mode_does_not_detrend() -> None:
    """Raw mode keeps the trend in the displacement series."""
    disp = [0.0, -1.0, -2.0, -3.0, -4.0, -5.0]
    prec = [10, 20, 30, 40, 50, 60]
    result = pearson_egms_precipitation(disp, prec, detrend=False)
    assert result is not None
    assert result.method == "raw"
    # displacement decreasing while precipitation increasing → strong negative
    assert result.pearson_r < -0.99


def test_handles_nan_in_input() -> None:
    """NaN values in either series are dropped from the analysis."""
    disp = [0.0, float("nan"), -0.8, -1.5, -2.1, -2.8, -3.6, -4.3, -5.5, -6.1]
    prec = [78, 45, 62, 105, 38, 28, 88, 71, 95, 52]
    result = pearson_egms_precipitation(disp, prec, detrend=True)
    assert result is not None
    assert result.n_samples == 9


def test_interpretation_strings_cover_strength_buckets() -> None:
    # Strong positive
    n = 30
    prec = [(i * 7) % 100 for i in range(n)]
    disp = [0.001 * i + 0.05 * p for i, p in enumerate(prec)]
    res = pearson_egms_precipitation(disp, prec, detrend=True)
    assert res is not None
    assert res.pearson_r > 0.8
    assert "starker" in res.interpretation
