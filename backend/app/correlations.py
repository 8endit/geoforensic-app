"""Statistical correlations between EGMS displacement and other drivers.

Used to populate ``velocity_timeseries.correlation_coefficient`` and
``correlation_radar.correlation_coefficient`` in the visuals payload.

Methodology
-----------
Buyers want to know whether the observed ground motion is **structural**
(monotonic settlement, e.g. soil compaction or active subsidence) or
**driven by precipitation** (seasonal swelling/shrinking of clay-rich
soils). A naive Pearson correlation between raw displacement and
rainfall is not informative because the steady-state settlement trend
dominates the signal.

The right test is:

1. Fit a linear trend to the displacement time-series and subtract it
   (detrending).
2. Compute Pearson r between the detrended residuals and the
   precipitation time-series.

A high positive r on the detrended series means the seasonal residual
co-varies with rainfall — a precipitation-driven signal. A near-zero r
on the detrended series, combined with a non-zero trend slope, means
the motion is structural and **not** explained by rainfall.

Note on the example payload
---------------------------
``docs/visuals/example_payload.json`` shows ``correlation_coefficient =
0.71`` for the Schulstraße 12 series. That value was authored by hand
to illustrate a precipitation-driven case; the actual displacement
series in the payload is monotonic and yields a much lower r when
computed. This module computes the real number from real data — the
0.71 is illustrative only and not a regression target.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Optional, Sequence

logger = logging.getLogger(__name__)


@dataclass
class CorrelationResult:
    pearson_r: float
    p_value: float
    n_samples: int
    method: str  # "raw" | "detrended"
    interpretation: str

    def to_dict(self) -> dict:
        return asdict(self)


def _interpret(r: float, p: float, n: int) -> str:
    if n < 5:
        return "Stichprobe zu klein für belastbare Aussage"
    if p > 0.1:
        return "kein signifikanter Zusammenhang nachweisbar"
    abs_r = abs(r)
    sign = "positiv" if r > 0 else "negativ"
    if abs_r < 0.3:
        strength = "schwacher"
    elif abs_r < 0.6:
        strength = "moderater"
    elif abs_r < 0.8:
        strength = "deutlicher"
    else:
        strength = "starker"
    return f"{strength} {sign} Zusammenhang"


def pearson_egms_precipitation(
    displacement_mm: Sequence[float],
    precipitation_mm: Sequence[float],
    detrend: bool = True,
) -> Optional[CorrelationResult]:
    """Pearson correlation between displacement and precipitation.

    Both series must be aligned in time (same index = same date) and
    have at least 4 paired observations. ``detrend=True`` removes a
    linear trend from the displacement before correlating — this
    isolates the seasonal component, which is what should correlate
    with rainfall if the motion is precipitation-driven.

    Returns ``None`` if either series is too short or contains
    incompatible NaN/None patterns.
    """
    if len(displacement_mm) != len(precipitation_mm):
        logger.warning(
            "displacement (%d) and precipitation (%d) series must have equal length",
            len(displacement_mm),
            len(precipitation_mm),
        )
        return None
    if len(displacement_mm) < 4:
        return None

    try:
        import numpy as np
        from scipy.stats import pearsonr
    except ImportError:  # pragma: no cover
        logger.error("scipy not available; cannot compute Pearson correlation")
        return None

    disp = np.asarray(displacement_mm, dtype=float)
    prec = np.asarray(precipitation_mm, dtype=float)

    # Drop indices where either series has NaN
    mask = ~(np.isnan(disp) | np.isnan(prec))
    disp = disp[mask]
    prec = prec[mask]
    n = int(len(disp))
    if n < 4:
        return None

    method = "detrended" if detrend else "raw"
    if detrend:
        t = np.arange(n, dtype=float)
        slope, intercept = np.polyfit(t, disp, 1)
        disp = disp - (slope * t + intercept)

    # Constant series → undefined correlation
    if np.std(disp) == 0 or np.std(prec) == 0:
        return None

    r, p = pearsonr(disp, prec)
    return CorrelationResult(
        pearson_r=float(r),
        p_value=float(p),
        n_samples=n,
        method=method,
        interpretation=_interpret(float(r), float(p), n),
    )
