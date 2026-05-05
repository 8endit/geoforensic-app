"""Aggregator that builds the visuals data-contract payload.

This module is the **single assembly point** for the JSON object that
the SVG templates consume. It takes already-fetched data from the
existing pipeline modules (EGMS, SoilGrids, slope, KOSTRA, geology,
building footprint, …) and produces a dict matching
``docs/visuals/data_contract.json``.

It does not fetch anything itself — that keeps the function pure and
deterministic, easy to test against the Schulstraße-12 example payload.
The live integration (which calls ``egms_query()``,
``soil_data.SoilDataLoader``, ``query_geology``, etc.) lives in
``routers/leads.py`` and constructs the input bundle for this builder.

Structure
---------
``build_payload(...)`` is the entry point. Each component is built by a
private helper (``_build_risk_dashboard``, ``_build_property_context_map``,
…) so individual sections can be tested or partially populated when a
data source fails. Missing inputs degrade gracefully — required fields
get sentinel values, optional fields are dropped.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Optional

from app.burland_classifier import (
    BurlandResult,
    OverallGrade,
    classify as classify_burland,
    compute_overall_grade,
    data_quality_from_psi_count,
)
from app.correlations import CorrelationResult, pearson_egms_precipitation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trend_category(burland_class: int) -> tuple[str, str]:
    """Map Burland class → trend label + description.

    The ``trend`` enum in the data contract was authored before the
    classifier; it categorizes how the displacement progresses. We map
    it deterministically from the Burland class to keep the dashboard
    and the trend display coherent — Burland ≤ 2 = "stabil", 3 =
    "leicht beschleunigend", 4–6 = "beschleunigend".
    """
    if burland_class <= 2:
        return "stabil", "leichte saisonale Schwankung"
    if burland_class == 3:
        return "leicht beschleunigend", "Setzungsrate moderat über Rauschpegel"
    return "beschleunigend", "Setzungsrate deutlich über Rauschpegel"


def _data_quality_description(psi_count: int, mean_coherence: Optional[float]) -> str:
    """Compact description for the Datenqualität-Box (≈ 32-Char-Budget).

    The PSI count + radius is already shown in the dashboard's PSI-Punkte
    box right below, so we drop „im 500 m-Radius" here to avoid overflow.
    """
    parts = [f"{psi_count} PSI"]
    if mean_coherence is not None and not (mean_coherence != mean_coherence):  # not NaN
        parts.append(f"Kohärenz {mean_coherence:.2f}")
    return " · ".join(parts)


def _linear_trend_slope(series: list[dict]) -> Optional[float]:
    """Compute mm/year from a date-displacement series via linear
    regression. Returns None if too few points."""
    if not series or len(series) < 3:
        return None
    try:
        import numpy as np
    except ImportError:  # pragma: no cover
        return None
    dates = []
    disps = []
    for p in series:
        try:
            d = datetime.fromisoformat(str(p["date"]).replace("Z", "+00:00"))
            dates.append(d.timestamp())
            disps.append(float(p["displacement_mm"]))
        except (KeyError, ValueError, TypeError):
            continue
    if len(dates) < 3:
        return None
    t = np.asarray(dates)
    y = np.asarray(disps)
    # slope is mm per second; convert to mm per year
    slope_per_sec, _ = np.polyfit(t, y, 1)
    return float(slope_per_sec * 365.25 * 24 * 3600)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _mean_velocity_k_nearest(
    psi_points: list[dict],
    lat: float,
    lon: float,
    k: int = 3,
) -> Optional[float]:
    """Mean velocity of the k PSI points nearest to (lat, lon).

    This is the dashboard's "velocity_mm_per_year" — it represents the
    actual property's signal, not the 500 m-radius neighborhood
    average. The neighborhood average is used for the histogram only.
    """
    pairs: list[tuple[float, float]] = []
    for p in psi_points:
        try:
            d = _haversine_m(lat, lon, float(p["lat"]), float(p["lon"]))
            pairs.append((d, float(p["velocity"])))
        except (KeyError, ValueError, TypeError):
            continue
    if not pairs:
        return None
    pairs.sort(key=lambda t: t[0])
    nearest = pairs[: min(k, len(pairs))]
    return sum(v for _, v in nearest) / len(nearest)


def _norm(value: float, lo: float, hi: float) -> float:
    """Linear normalisation to 0-5, clamped at both ends."""
    if hi == lo:
        return 0.0
    v = (value - lo) / (hi - lo) * 5.0
    return max(0.0, min(5.0, v))


# ---------------------------------------------------------------------------
# Component builders
# ---------------------------------------------------------------------------

def _build_risk_dashboard(
    burland: Optional[BurlandResult],
    overall: OverallGrade,
    mean_velocity: float,
    psi_count: int,
    mean_coherence: Optional[float],
) -> dict:
    mean_v = mean_velocity

    if burland is not None:
        trend, trend_desc = _trend_category(burland.burland_class)
        return {
            "burland_class": burland.burland_class,
            "burland_label": burland.label,
            "burland_description": burland.description,
            "velocity_mm_per_year": round(mean_v, 2),
            "velocity_basis": burland.velocity_basis,
            "trend": trend,
            "trend_description": trend_desc,
            "data_quality": overall.data_quality,
            "data_quality_description": _data_quality_description(psi_count, mean_coherence),
            "psi_count_in_radius": psi_count,
            "overall_grade": overall.grade,
            "overall_grade_label": overall.label,
            "overall_grade_recommendation": overall.recommendation,
        }

    # No burland → minimal dashboard with sentinels.
    return {
        "burland_class": 1,
        "burland_label": "stabil",
        "burland_description": "Keine Bewegungsdaten verfügbar — Default-Wert.",
        "velocity_mm_per_year": 0.0,
        "velocity_basis": "keine Daten",
        "trend": "uneindeutig",
        "trend_description": "Datenlage zu dünn",
        "data_quality": overall.data_quality,
        "data_quality_description": _data_quality_description(psi_count, mean_coherence),
        "psi_count_in_radius": psi_count,
        "overall_grade": overall.grade,
        "overall_grade_label": overall.label,
        "overall_grade_recommendation": overall.recommendation,
    }


def _build_property_context_map(
    radius_m: int,
    psi_points: list[dict],
    building_footprint: Optional[dict],
) -> dict:
    cleaned = []
    for p in psi_points:
        try:
            cleaned.append({
                "lat": float(p["lat"]),
                "lon": float(p["lon"]),
                "velocity": float(p["velocity"]),
                **({"coherence": float(p["coherence"])} if "coherence" in p else {}),
            })
        except (KeyError, ValueError, TypeError):
            continue

    bf: Optional[dict] = None
    if building_footprint and building_footprint.get("available"):
        bf = {
            "polygon": building_footprint.get("polygon"),
            "centroid": building_footprint.get("centroid"),
        }
    return {
        "radius_meters": radius_m,
        "psi_points": cleaned,
        "building_footprint": bf,
    }


def _build_velocity_timeseries(
    psi_series: list[dict],
    precipitation_series: Optional[list[dict]],
) -> dict:
    series = [
        {"date": p["date"], "displacement_mm": float(p["displacement_mm"])}
        for p in psi_series if "date" in p and "displacement_mm" in p
    ]
    series.sort(key=lambda x: x["date"])
    start_date = series[0]["date"] if series else None
    end_date = series[-1]["date"] if series else None
    slope = _linear_trend_slope(series)

    out: dict[str, Any] = {
        "start_date": start_date,
        "end_date": end_date,
        "psi_series": series,
    }

    correlation: Optional[CorrelationResult] = None
    if precipitation_series:
        prec = [
            {"date": p["date"], "mm": float(p["mm"])}
            for p in precipitation_series if "date" in p and "mm" in p
        ]
        prec.sort(key=lambda x: x["date"])
        out["precipitation_series"] = prec
        if len(series) == len(prec) and len(series) >= 4:
            correlation = pearson_egms_precipitation(
                [p["displacement_mm"] for p in series],
                [p["mm"] for p in prec],
                detrend=True,
            )

    if slope is not None:
        out["trend_slope_mm_per_year"] = round(slope, 3)
    if correlation is not None:
        out["correlation_coefficient"] = round(correlation.pearson_r, 3)
    return out


def _build_soil_context_stack(
    sealing_percent: Optional[float],
    soil_layers: Optional[list[dict]],
    geology: Optional[dict],
    has_building: bool,
    groundwater_depth_m: Optional[float],
) -> dict:
    layers = list(soil_layers) if soil_layers else _default_layers(geology)
    out: dict[str, Any] = {
        "depth_m": layers[-1]["depth_bottom_m"] if layers else 5,
        "has_building": has_building,
        "layers": layers,
    }
    if sealing_percent is not None:
        out["sealing_percent"] = round(float(sealing_percent), 1)
    if groundwater_depth_m is not None:
        out["groundwater_depth_m"] = round(float(groundwater_depth_m), 2)
    return out


def _default_layers(geology: Optional[dict]) -> list[dict]:
    """Construct a sensible 4-layer stack from geology data alone when
    no SoilGrids/LUCAS profile is supplied."""
    layers: list[dict] = [
        {
            "type": "topsoil",
            "depth_top_m": 0.0,
            "depth_bottom_m": 0.3,
            "label": "Mutterboden",
            "source": "SoilGrids 250m",
        },
        {
            "type": "subsoil",
            "depth_top_m": 0.3,
            "depth_bottom_m": 2.4,
            "label": "Lehm und Schluff",
            "source": "SoilGrids 250m",
        },
        {
            "type": "weathered",
            "depth_top_m": 2.4,
            "depth_bottom_m": 4.0,
            "label": "Verwitterungszone",
            "source": "BGR GÜK250",
        },
        {
            "type": "bedrock",
            "depth_top_m": 4.0,
            "depth_bottom_m": 5.0,
            "label": "Festgestein",
            "source": "BGR GÜK250",
        },
    ]
    if geology and geology.get("available"):
        rock = geology.get("rock_type_short") or geology.get("rock_type")
        if rock:
            layers[-1]["label"] = rock
        if geology.get("stratigraphy"):
            layers[-1]["source"] = f"BGR GÜK250 — {geology['stratigraphy']}"
    return layers


def _build_correlation_radar(
    mean_velocity: float,
    annual_precipitation_mm: Optional[float],
    sealing_percent: Optional[float],
    clay_percent: Optional[float],
    slope_degrees: Optional[float],
    groundwater_depth_m: Optional[float],
    correlation_r: Optional[float],
) -> dict:
    """Build the 6-axis radar with normalised values 0-5.

    Normalisation choices (approximate, calibrated for typical residential
    DE addresses):
      velocity        |v| 0…5 mm/yr     → 0…5
      precipitation   500…1500 mm/yr    → 0…5
      sealing         0…100 %           → 0…5
      swelling_clay   0…40 % clay       → 0…5
      slope           0…10 °            → 0…5
      groundwater     -10…0 m depth     → 0…5 (nearer surface = higher score)
    """
    axes: list[dict] = []

    # Velocity
    axes.append({
        "name": "velocity",
        "label": "Velocity",
        "value": round(_norm(abs(mean_velocity), 0, 5), 2),
        "raw_value": f"{mean_velocity:+.1f} mm/J",
        "unit": "mm/Jahr",
    })

    # Precipitation
    if annual_precipitation_mm is not None:
        axes.append({
            "name": "precipitation",
            "label": "Niederschlag",
            "value": round(_norm(annual_precipitation_mm, 500, 1500), 2),
            "raw_value": f"{annual_precipitation_mm:.0f} mm/Jahr",
            "unit": "mm/Jahr",
        })
    else:
        axes.append({
            "name": "precipitation", "label": "Niederschlag", "value": None,
            "raw_value": "n/a", "unit": "mm/Jahr",
        })

    # Sealing
    if sealing_percent is not None:
        axes.append({
            "name": "sealing", "label": "Versiegelung",
            "value": round(_norm(sealing_percent, 0, 100), 2),
            "raw_value": f"{sealing_percent:.0f} %", "unit": "%",
        })
    else:
        axes.append({
            "name": "sealing", "label": "Versiegelung", "value": None,
            "raw_value": "n/a", "unit": "%",
        })

    # Swelling clay
    if clay_percent is not None:
        axes.append({
            "name": "swelling_clay", "label": "Quelltonanteil",
            "value": round(_norm(clay_percent, 0, 40), 2),
            "raw_value": f"{clay_percent:.0f} % Ton", "unit": "%",
        })
    else:
        axes.append({
            "name": "swelling_clay", "label": "Quelltonanteil", "value": None,
            "raw_value": "n/a", "unit": "%",
        })

    # Slope
    if slope_degrees is not None:
        axes.append({
            "name": "slope", "label": "Hangneigung",
            "value": round(_norm(slope_degrees, 0, 10), 2),
            "raw_value": f"{slope_degrees:.1f} °", "unit": "°",
        })
    else:
        axes.append({
            "name": "slope", "label": "Hangneigung", "value": None,
            "raw_value": "n/a", "unit": "°",
        })

    # Groundwater (nearer surface = higher risk score)
    if groundwater_depth_m is not None:
        # depth is negative (e.g. -2.4 = 2.4m below surface)
        score = round(_norm(-groundwater_depth_m, 0, 10), 2)
        # Invert: shallow water (small depth) = high score
        score = round(5 - score, 2)
        axes.append({
            "name": "groundwater", "label": "Grundwasser",
            "value": score,
            "raw_value": f"{groundwater_depth_m:+.1f} m", "unit": "m",
        })
    else:
        axes.append({
            "name": "groundwater", "label": "Grundwasser", "value": None,
            "raw_value": "n/a", "unit": "m",
        })

    # Dominant driver: axis with highest non-null value
    scored = [(a["value"], a) for a in axes if a["value"] is not None]
    scored.sort(key=lambda t: t[0], reverse=True)
    if scored:
        dominant = scored[0][1]
        dom_name = dominant["name"]
        dom_label = dominant["label"]
    else:
        dom_name, dom_label = "velocity", "Velocity"

    interp_parts = [f"Stärkster Treiber: {dom_label}"]
    if correlation_r is not None:
        interp_parts.append(f"Korrelation r = {correlation_r:.2f}")
        if abs(correlation_r) < 0.3:
            interp_parts.append("kein nachweisbarer Zusammenhang")
        elif correlation_r > 0:
            interp_parts.append("saisonal-getrieben")
        else:
            interp_parts.append("strukturell, nicht regen-getrieben")

    return {
        "axes": axes,
        "dominant_driver": dom_name,
        "correlation_coefficient": round(correlation_r, 3) if correlation_r is not None else None,
        "interpretation": " · ".join(interp_parts),
    }


def _build_neighborhood_histogram(
    velocities_mm_per_year: list[float],
    own_velocity: float,
) -> dict:
    """Bin velocities adaptiv basierend auf Streuung der Nachbarschaft.

    Vorher: Fest -5…+5 mm/yr in 1 mm-Schritten. Bei dichten Stadt-Lagen
    (Berlin-Mitte: alle 78 Punkte zwischen -1 und 0 mm/Jahr) ergab das
    EINEN Riesenbalken — die Visualisierung war wertlos.

    Jetzt: x-Range = Median ± max(2.5 × Std, 1 mm), Bin-Width abhängig
    von der Streuung (0.2/0.5/1.0 mm). Heißt für homogene Nachbarschaften
    sieht man die Feinverteilung, für heterogene bleibt die ±5-mm-Sicht.
    """
    try:
        import numpy as np
    except ImportError:  # pragma: no cover
        return {
            "bins": [], "own_velocity": own_velocity,
            "psi_count": len(velocities_mm_per_year),
            "interpretation": "Histogramm-Berechnung nicht verfügbar",
            "x_min": -5.0, "x_max": 5.0,
        }

    if not velocities_mm_per_year:
        return {
            "bins": [], "own_velocity": own_velocity, "psi_count": 0,
            "interpretation": "Keine PSI-Punkte im Radius",
            "x_min": -5.0, "x_max": 5.0,
        }

    arr = np.asarray(velocities_mm_per_year, dtype=float)
    median = float(np.median(arr))
    std = float(np.std(arr))
    spread_mm = float(arr.max() - arr.min())

    # Adaptive Bin-Width + Range
    if std < 0.5:
        bin_width = 0.2
        x_min = round(median - 1.5, 1)
        x_max = round(median + 1.5, 1)
        spread_label = "sehr homogen"
    elif std < 2.0:
        bin_width = 0.5
        x_min = round(median - 3.0, 1)
        x_max = round(median + 3.0, 1)
        spread_label = "ähnlich"
    else:
        bin_width = 1.0
        x_min, x_max = -5.0, 5.0
        spread_label = "heterogen"

    edges = np.arange(x_min, x_max + bin_width, bin_width)
    counts, _ = np.histogram(arr, bins=edges)
    bins = [
        {"min": float(edges[i]), "max": float(edges[i + 1]), "count": int(counts[i])}
        for i in range(len(counts))
        if counts[i] > 0
    ]

    # Percentile of own velocity in distribution (0=most stable, 100=most extreme)
    sorted_vals = np.sort(np.abs(arr))
    own_abs = abs(own_velocity)
    rank = np.searchsorted(sorted_vals, own_abs, side="right")
    percentile = int(round(100 * rank / len(sorted_vals)))

    if percentile <= 25:
        ranking = "im stabilen Bereich der Nachbarschaft"
    elif percentile <= 60:
        ranking = "im unauffälligen Mittelbereich"
    elif percentile <= 85:
        ranking = "über dem Median der Nachbarschaft"
    else:
        ranking = "im auffälligen Randbereich"

    interp = (
        f"Nachbarschaft {spread_label} (Spannweite {spread_mm:.1f} mm/Jahr). "
        f"Ihr Standort liegt {ranking}."
    )

    return {
        "bins": bins,
        "own_velocity": round(float(own_velocity), 2),
        "psi_count": int(len(arr)),
        "percentile": percentile,
        "interpretation": interp,
        "x_min": float(x_min),
        "x_max": float(x_max),
        "neighborhood_median_mm_per_year": round(median, 2),
        "neighborhood_std_mm_per_year": round(std, 2),
    }


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def build_payload(
    *,
    address: dict,
    psi_points: list[dict],
    psi_timeseries: list[dict],
    precipitation_series: Optional[list[dict]] = None,
    annual_precipitation_mm: Optional[float] = None,
    soil_layers: Optional[list[dict]] = None,
    sealing_percent: Optional[float] = None,
    clay_percent: Optional[float] = None,
    slope_degrees: Optional[float] = None,
    groundwater_depth_m: Optional[float] = None,
    geology: Optional[dict] = None,
    building_footprint: Optional[dict] = None,
    radius_meters: int = 500,
    tier: str = "free",
    report_id: Optional[str] = None,
    data_sources_used: Optional[list[str]] = None,
    data_sources_missing: Optional[list[str]] = None,
) -> dict:
    """Aggregate pipeline outputs into the visuals data-contract payload.

    All non-required inputs may be ``None`` — the corresponding
    component falls back to sensible defaults or skip patterns. The
    result validates against ``docs/visuals/data_contract.json``.
    """
    # PSI summary
    velocities = [float(p["velocity"]) for p in psi_points if "velocity" in p]
    coherences = [float(p["coherence"]) for p in psi_points if "coherence" in p]
    mean_coherence = sum(coherences) / len(coherences) if coherences else None
    radius_mean_velocity = sum(velocities) / len(velocities) if velocities else 0.0
    max_velocity = max(velocities, key=abs) if velocities else None
    psi_count = len(psi_points)

    # Dashboard velocity is mean of k=3 nearest PSI to the address (the
    # actual property signal). The radius-mean is reserved for the
    # neighborhood histogram interpretation.
    nearest_mean = _mean_velocity_k_nearest(
        psi_points, address["lat"], address["lon"], k=3
    )
    mean_velocity = nearest_mean if nearest_mean is not None else radius_mean_velocity

    # Linear trend (used both for Burland and for the timeseries section)
    trend_slope = _linear_trend_slope(psi_timeseries) if psi_timeseries else None

    burland = classify_burland(
        mean_velocity_mm_per_year=mean_velocity,
        max_velocity_mm_per_year=max_velocity,
        trend_slope_mm_per_year=trend_slope,
        psi_count=psi_count,
    )
    if burland is not None and nearest_mean is not None:
        burland.velocity_basis = "Mittel der drei nächsten PSI"
    overall = compute_overall_grade(burland, psi_count=psi_count)

    components = {
        "risk_dashboard": _build_risk_dashboard(
            burland=burland,
            overall=overall,
            mean_velocity=mean_velocity,
            psi_count=psi_count,
            mean_coherence=mean_coherence,
        ),
        "property_context_map": _build_property_context_map(
            radius_m=radius_meters,
            psi_points=psi_points,
            building_footprint=building_footprint,
        ),
        "velocity_timeseries": _build_velocity_timeseries(
            psi_series=psi_timeseries,
            precipitation_series=precipitation_series,
        ),
        "soil_context_stack": _build_soil_context_stack(
            sealing_percent=sealing_percent,
            soil_layers=soil_layers,
            geology=geology,
            has_building=bool(building_footprint and building_footprint.get("available")),
            groundwater_depth_m=groundwater_depth_m,
        ),
    }

    # Correlation needs the r value computed in velocity_timeseries
    corr_r = components["velocity_timeseries"].get("correlation_coefficient")
    components["correlation_radar"] = _build_correlation_radar(
        mean_velocity=mean_velocity,
        annual_precipitation_mm=annual_precipitation_mm,
        sealing_percent=sealing_percent,
        clay_percent=clay_percent,
        slope_degrees=slope_degrees,
        groundwater_depth_m=groundwater_depth_m,
        correlation_r=corr_r,
    )

    components["neighborhood_histogram"] = _build_neighborhood_histogram(
        velocities_mm_per_year=velocities,
        own_velocity=mean_velocity,
    )

    payload: dict[str, Any] = {
        "report_id": report_id or _default_report_id(),
        "tier": tier,
        "address": address,
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "data_sources_used": data_sources_used or [],
            "data_sources_missing": data_sources_missing or [],
        },
        "components": components,
    }
    return payload


def _default_report_id() -> str:
    now = datetime.now(timezone.utc)
    return f"GF-{now.strftime('%Y-%m-%d-%H%M%S')}"
