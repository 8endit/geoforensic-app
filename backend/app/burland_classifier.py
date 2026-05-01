"""Burland-style classification of ground motion impact on buildings.

Maps measured InSAR velocity (mm/year) to a 6-step damage-risk class. The
classification is inspired by Burland & Wroth (1974) and Burland, Mair &
Standing (1995) "Settlement of Buildings and Associated Damage", which
relates total settlement and angular distortion to damage categories.

Adaptation for our use case
---------------------------
The original Burland scheme keys off total settlement and angular
distortion at building scale. We do not measure the building directly —
we measure the surrounding ground via Sentinel-1 PSI scatterers. So we
classify by **annual velocity** (the steady-state rate that, projected
out, drives the cumulative settlement) plus a trend modifier.

Class boundaries are calibrated so that:
- class 1 (stabil) corresponds to noise-floor velocity
- class 2 (leicht) is the seasonal/thermal-cycle band where most
  buildings sit
- class 3 (moderat) is where observation should start
- class 4 (auffällig) crosses the 3 mm/yr threshold widely cited in
  EGMS/BBD reporting as "needs explanation"
- class 5 (erheblich) and class 6 (kritisch) trigger expert review and
  immediate action, respectively

These thresholds align with the SPEC_VISUALS.md §3 ampel-Farbsystem.

The function is intentionally pure (no I/O, no config). It is called from
``visual_payload.build_payload()`` after the EGMS query has produced
mean/max velocity and trend-slope.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

# Class boundaries on |velocity| in mm/year. Index i is the threshold
# between class (i+1) and class (i+2), so a value below THRESHOLDS[0]
# is class 1, a value in [THRESHOLDS[0], THRESHOLDS[1]) is class 2, etc.
THRESHOLDS = [0.5, 1.5, 3.0, 5.0, 10.0]

LABELS = ["stabil", "leicht", "moderat", "auffällig", "erheblich", "kritisch"]

DESCRIPTIONS = [
    "0–±0,5 mm/Jahr — keine messbare Bewegung über dem Sentinel-1-Rauschpegel",
    "±0,5–±1,5 mm/Jahr — saisonale Schwankung, typisch für stabile Bestandsbauten",
    "±1,5–±3,0 mm/Jahr — moderate Bewegung, regelmäßige Beobachtung empfohlen",
    "±3,0–±5,0 mm/Jahr — auffällige Setzung, fachgutachterliche Bewertung empfehlenswert",
    "±5,0–±10,0 mm/Jahr — erhebliche Bewegung, dringende Klärung der Ursache",
    ">±10,0 mm/Jahr — kritische Bewegungsrate, sofortige fachliche Klärung erforderlich",
]


@dataclass
class BurlandResult:
    burland_class: int
    label: str
    description: str
    velocity_basis: str
    trend_modifier_applied: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _classify_by_magnitude(magnitude_mm_per_year: float) -> int:
    """Return Burland class (1-6) from |velocity| in mm/year."""
    cls = 1
    for i, t in enumerate(THRESHOLDS):
        if magnitude_mm_per_year >= t:
            cls = i + 2
    return min(cls, 6)


def classify(
    mean_velocity_mm_per_year: Optional[float],
    max_velocity_mm_per_year: Optional[float] = None,
    trend_slope_mm_per_year: Optional[float] = None,
    psi_count: Optional[int] = None,
) -> Optional[BurlandResult]:
    """Classify a property by Burland-inspired ground-motion impact.

    Parameters
    ----------
    mean_velocity_mm_per_year:
        Mean PSI velocity in the search radius. Negative = settling,
        positive = heave. Required.
    max_velocity_mm_per_year:
        Worst-case PSI velocity in the search radius. Used as a sanity
        check: if the worst PSI is one full class above the mean, the
        result is bumped up by one (capped at 6).
    trend_slope_mm_per_year:
        Slope of the linear regression on the velocity time-series. If
        the trend is significantly steeper than the mean (i.e. the
        movement is accelerating), bump up by one class.
    psi_count:
        Number of PSI points in the radius. Drives the data-quality
        annotation but does NOT affect the class itself.

    Returns
    -------
    ``BurlandResult`` or ``None`` if mean_velocity is missing — caller
    is responsible for handling sparse-data fallback.
    """
    if mean_velocity_mm_per_year is None:
        return None

    base = abs(mean_velocity_mm_per_year)
    cls = _classify_by_magnitude(base)
    velocity_basis = "Mittel der PSI im Radius"

    # Trend-modifier: if the movement is clearly accelerating (trend
    # slope > 1.5x the mean and at least 0.5 mm/yr above it), bump one
    # class. This catches cases where seasonal averaging masks an
    # ongoing acceleration.
    trend_bumped = False
    if trend_slope_mm_per_year is not None and base > 0:
        trend_mag = abs(trend_slope_mm_per_year)
        if trend_mag > 1.5 * base and trend_mag - base >= 0.5:
            cls = min(cls + 1, 6)
            trend_bumped = True
            velocity_basis = "Mittel der PSI + Trend-Modifier"

    # Max-velocity check: if the worst PSI is one full class above the
    # current class (using the same threshold table), bump once. This
    # protects against averaging out a clearly worse hot-spot.
    if max_velocity_mm_per_year is not None:
        max_cls = _classify_by_magnitude(abs(max_velocity_mm_per_year))
        if max_cls >= cls + 2:
            cls = min(cls + 1, 6)
            velocity_basis = "Mittel der PSI + Max-Modifier"

    return BurlandResult(
        burland_class=cls,
        label=LABELS[cls - 1],
        description=DESCRIPTIONS[cls - 1],
        velocity_basis=velocity_basis,
        trend_modifier_applied=trend_bumped,
    )


# ---------------------------------------------------------------------------
# Overall A-E grade
# ---------------------------------------------------------------------------
#
# The A-E grade is the headline number on the cover page of the report. It
# combines the Burland class with data-quality (driven by PSI count). The
# rule is intentionally simple and explainable:
#
#   - PSI count < 3   → grade is automatically "—" (data quality too low to
#                       state a grade); caller renders this as a "Daten zu
#                       dünn" badge instead of an A-E circle.
#   - Otherwise the grade follows the Burland class:
#       class 1       → A (unauffällig)
#       class 2       → B (leichte Schwankung)
#       class 3       → C (beobachten)
#       class 4       → D (auffällig)
#       class 5–6     → E (erheblich/kritisch)
#   - With one downgrade rule: if data quality is "begrenzt" (3 ≤ PSI < 10)
#     and the class is 1 or 2, the grade is capped at B (we never claim A
#     on thin data).

_GRADE_BY_CLASS = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E", 6: "E"}
_GRADE_LABEL = {
    "A": "unauffällig",
    "B": "leichte Schwankung",
    "C": "beobachten",
    "D": "auffällig",
    "E": "erheblich",
}
_GRADE_RECOMMENDATION = {
    # Compact phrasing — fits the 32-char budget of the dashboard's
    # Gesamtbewertung box (210 px wide at font-size 11). Longer prose
    # belongs in the report body, not on a data-viz tile.
    "A": "Routinebeobachtung",
    "B": "Routinebeobachtung",
    "C": "Wiederholungsmessung in 12 Mon.",
    "D": "Fachgutachten empfohlen",
    "E": "Dringend fachgutachterlich klären",
}


@dataclass
class OverallGrade:
    grade: str  # "A".."E" or "—"
    label: str
    recommendation: str
    data_quality: str  # "hoch" | "mittel" | "begrenzt" | "niedrig"

    def to_dict(self) -> dict:
        return asdict(self)


def data_quality_from_psi_count(psi_count: Optional[int]) -> str:
    """Return one of: hoch / mittel / begrenzt / niedrig."""
    if psi_count is None or psi_count < 3:
        return "niedrig"
    if psi_count < 10:
        return "begrenzt"
    if psi_count < 30:
        return "mittel"
    return "hoch"


def compute_overall_grade(
    burland_result: Optional[BurlandResult],
    psi_count: Optional[int],
) -> OverallGrade:
    quality = data_quality_from_psi_count(psi_count)

    if burland_result is None or quality == "niedrig":
        return OverallGrade(
            grade="—",
            label="nicht bewertbar",
            recommendation="Datenlage zu dünn für eine A–E-Bewertung. PSI-Punktdichte im 500 m-Radius unter Mindestschwelle.",
            data_quality=quality,
        )

    grade = _GRADE_BY_CLASS[burland_result.burland_class]
    if quality == "begrenzt" and grade == "A":
        grade = "B"

    return OverallGrade(
        grade=grade,
        label=_GRADE_LABEL[grade],
        recommendation=_GRADE_RECOMMENDATION[grade],
        data_quality=quality,
    )
