"""Render-context builders for the four Tier-2 chart templates.

Each chart template is declarative SVG — Jinja decides what to draw,
not how to scale or project. This module pre-computes the geometry
(axis ticks, bar heights, line points, polygon vertices, bin
positions) so the templates stay readable.

Conventions
-----------
- All builders return plain dicts (not dataclasses) so the templates
  can do ``ctx.foo.bar`` without ``.to_dict()`` plumbing.
- All builders are pure: no I/O, no module-level state. Tokens are
  passed in or loaded once.
- All builders handle missing/empty inputs gracefully — the result
  contains an ``available`` flag so the template can show a "—" or
  "Daten in Vorbereitung" panel.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Velocity timeseries — Komponente 3
# ---------------------------------------------------------------------------

def _parse_iso_date(s: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def build_timeseries_render_context(
    component: dict,
    chart_x: int = 80,
    chart_y: int = 80,
    chart_width: int = 560,
    chart_height: int = 160,
) -> dict:
    """Project a velocity_timeseries component onto pixel space.

    Output keys consumed by the template:
      chart_x, chart_y, chart_width, chart_height
      y_zero_px, y_top_px, y_bottom_px       — for the zero-line and Y axis
      y_ticks   list of {value, y_px}        — Y-axis labels
      psi_pts   list of {x_px, y_px}         — PSI points on the line
      psi_path  SVG path d                   — connecting line
      rain_bars list of {x_px, y_px, w, h}   — precipitation bars
      trend     dict or None                 — {x1,y1,x2,y2,slope_mm_per_year}
      x_year_ticks list of {label, x_px}     — X-axis year labels
      correlation_r  float or None           — Pearson r from upstream
      available bool
    """
    psi_series = component.get("psi_series") or []
    precip_series = component.get("precipitation_series") or []

    # Parse + sort PSI series
    parsed_psi: list[tuple[datetime, float]] = []
    for p in psi_series:
        d = _parse_iso_date(str(p.get("date", "")))
        if d is None:
            continue
        try:
            disp = float(p["displacement_mm"])
        except (KeyError, ValueError, TypeError):
            continue
        parsed_psi.append((d, disp))
    parsed_psi.sort(key=lambda t: t[0])

    if len(parsed_psi) < 2:
        return {"available": False, "chart_x": chart_x, "chart_y": chart_y,
                "chart_width": chart_width, "chart_height": chart_height}

    t_min = parsed_psi[0][0]
    t_max = parsed_psi[-1][0]
    t_span = (t_max - t_min).total_seconds()
    if t_span <= 0:
        return {"available": False}

    # Y-axis range: zoom on data, but always include zero
    disps = [d for _, d in parsed_psi]
    y_min_data = min(disps)
    y_max_data = max(disps)
    # Pad the range by 10% and ensure 0 is inside
    pad = max(1.0, (y_max_data - y_min_data) * 0.10)
    y_top = max(y_max_data + pad, 0.5)
    y_bot = min(y_min_data - pad, -0.5)

    def x_for_t(t: datetime) -> float:
        return chart_x + (t - t_min).total_seconds() / t_span * chart_width

    def y_for_v(v: float) -> float:
        return chart_y + (y_top - v) / (y_top - y_bot) * chart_height

    psi_pts = [{"x_px": x_for_t(t), "y_px": y_for_v(d)} for t, d in parsed_psi]
    psi_path = "M " + " L ".join(
        f"{p['x_px']:.1f} {p['y_px']:.1f}" for p in psi_pts
    )

    # Rain bars — scale heights against the precipitation maximum
    rain_bars: list[dict] = []
    if precip_series:
        parsed_rain = []
        for p in precip_series:
            d = _parse_iso_date(str(p.get("date", "")))
            if d is None:
                continue
            try:
                mm = float(p["mm"])
            except (KeyError, ValueError, TypeError):
                continue
            parsed_rain.append((d, mm))
        if parsed_rain:
            mm_max = max(mm for _, mm in parsed_rain) or 1.0
            # Bars sit in the lower 40% of the chart, max height = 60 px
            bar_h_max = 60.0
            bar_w = max(8.0, chart_width / max(len(parsed_rain), 1) * 0.6)
            for t, mm in parsed_rain:
                x = x_for_t(t) - bar_w / 2
                h = mm / mm_max * bar_h_max
                y = chart_y + chart_height - h
                rain_bars.append({"x_px": x, "y_px": y, "w": bar_w, "h": h, "mm": mm})

    # Linear trend (mm/year) — already in component, recompute geometry
    slope_per_year = component.get("trend_slope_mm_per_year")
    trend = None
    if slope_per_year is not None:
        # Compute intercept from the actual data so the line passes
        # through the cloud, not just from-end to-end of the simple slope.
        seconds = [(t - t_min).total_seconds() for t, _ in parsed_psi]
        slope_per_sec = float(slope_per_year) / (365.25 * 24 * 3600)
        # Least-squares-style intercept: mean(y) - slope * mean(t)
        mean_t = sum(seconds) / len(seconds)
        mean_y = sum(disps) / len(disps)
        intercept = mean_y - slope_per_sec * mean_t
        y_at_start = intercept
        y_at_end = intercept + slope_per_sec * t_span
        trend = {
            "x1": chart_x,
            "y1": y_for_v(y_at_start),
            "x2": chart_x + chart_width,
            "y2": y_for_v(y_at_end),
            "slope_mm_per_year": float(slope_per_year),
        }

    # Zero-line and Y-axis ticks
    y_zero_px = y_for_v(0.0)
    # Pick 4-5 round ticks in the data range
    span = y_top - y_bot
    if span <= 4:
        step = 1.0
    elif span <= 10:
        step = 2.0
    elif span <= 25:
        step = 5.0
    else:
        step = 10.0
    y_ticks = []
    v = math.floor(y_bot / step) * step
    while v <= y_top + 1e-6:
        if y_bot <= v <= y_top:
            y_ticks.append({"value": v, "y_px": y_for_v(v)})
        v += step

    # X-axis year ticks
    year_min = t_min.year
    year_max = t_max.year
    x_year_ticks = []
    for y in range(year_min, year_max + 1):
        t_year = datetime(y, 1, 1, tzinfo=t_min.tzinfo)
        if t_year < t_min or t_year > t_max:
            continue
        x_year_ticks.append({"label": str(y), "x_px": x_for_t(t_year)})

    return {
        "available": True,
        "chart_x": chart_x,
        "chart_y": chart_y,
        "chart_width": chart_width,
        "chart_height": chart_height,
        "y_top": y_top,
        "y_bottom": y_bot,
        "y_zero_px": y_zero_px,
        "y_ticks": y_ticks,
        "psi_pts": psi_pts,
        "psi_path": psi_path,
        "rain_bars": rain_bars,
        "trend": trend,
        "x_year_ticks": x_year_ticks,
        "start_date": component.get("start_date"),
        "end_date": component.get("end_date"),
        "correlation_r": component.get("correlation_coefficient"),
    }


# ---------------------------------------------------------------------------
# Soil context stack — Komponente 4
# ---------------------------------------------------------------------------

# Default colors for layer types — pulled from tokens.structural at runtime
# but kept here as a fallback if tokens aren't passed in.
_DEFAULT_LAYER_COLORS = {
    "topsoil":   "#FAC775",
    "subsoil":   "#EF9F27",
    "weathered": "#888780",
    "bedrock":   "#444441",
    "fill":      "#888780",
}


def build_soil_stack_render_context(
    component: dict,
    tokens: Optional[dict] = None,
    stack_x: int = 180,
    stack_y_top: int = 145,
    stack_width: int = 320,
    stack_height: int = 230,
) -> dict:
    """Project soil layers onto a vertical-cross-section coordinate system.

    The drawing area is ``stack_y_top`` (= 0 m surface) down to
    ``stack_y_top + stack_height`` (= depth_m metres). Building +
    sealing render above the surface line at fixed offsets.
    """
    layers = component.get("layers") or []
    depth_m = float(component.get("depth_m") or 5.0)
    has_building = bool(component.get("has_building"))
    sealing_pct = component.get("sealing_percent")
    groundwater = component.get("groundwater_depth_m")  # negative

    if tokens:
        struct = tokens.get("structural", {})
        layer_color = {
            "topsoil":   struct.get("topsoil",   {}).get("color", _DEFAULT_LAYER_COLORS["topsoil"]),
            "subsoil":   struct.get("subsoil",   {}).get("color", _DEFAULT_LAYER_COLORS["subsoil"]),
            "weathered": struct.get("weathered", {}).get("color", _DEFAULT_LAYER_COLORS["weathered"]),
            "bedrock":   struct.get("bedrock",   {}).get("color", _DEFAULT_LAYER_COLORS["bedrock"]),
            "fill":      struct.get("subsoil",   {}).get("color", _DEFAULT_LAYER_COLORS["fill"]),
        }
        bebauung_color = struct.get("bebauung", {}).get("color", "#5F5E5A")
        versiegelung_color = struct.get("versiegelung", {}).get("color", "#888780")
        groundwater_color = struct.get("groundwater", {}).get("color", "#185FA5")
    else:
        layer_color = dict(_DEFAULT_LAYER_COLORS)
        bebauung_color = "#5F5E5A"
        versiegelung_color = "#888780"
        groundwater_color = "#185FA5"

    def y_for_depth(d: float) -> float:
        """d in metres (positive = below surface) → pixel y."""
        return stack_y_top + (d / depth_m) * stack_height

    rendered_layers: list[dict] = []
    for layer in layers:
        try:
            top = float(layer["depth_top_m"])
            bot = float(layer["depth_bottom_m"])
        except (KeyError, ValueError, TypeError):
            continue
        y_top = y_for_depth(top)
        y_bot = y_for_depth(bot)
        rendered_layers.append({
            "type": layer.get("type", "subsoil"),
            "label": layer.get("label", ""),
            "source": layer.get("source"),
            "y": y_top,
            "h": max(2.0, y_bot - y_top),
            "y_mid": (y_top + y_bot) / 2.0,
            "color": layer_color.get(layer.get("type"), "#888780"),
            "soc_percent": layer.get("soc_percent"),
            "ph": layer.get("ph"),
        })

    # Building + sealing render ABOVE the stack (y_top - building_height)
    building_height = 50 if has_building else 0
    sealing_height = 22 if (sealing_pct is not None and sealing_pct > 0) else 0

    # Groundwater line: only if value is present
    groundwater_y = None
    if groundwater is not None:
        # groundwater is negative: -2.4 m means 2.4 m below surface
        gw_depth = abs(float(groundwater))
        if 0 <= gw_depth <= depth_m:
            groundwater_y = y_for_depth(gw_depth)

    # Depth-axis ticks every 1 m
    depth_ticks = []
    d = 0.0
    while d <= depth_m + 1e-6:
        depth_ticks.append({
            "depth_m": d,
            "y": y_for_depth(d),
            "label": "0 m" if d == 0 else f"−{int(round(d))} m",
        })
        d += 1.0

    # Building sits ABOVE sealing, sealing ABOVE ground (topsoil top).
    # Stacked from top of canvas down to stack_y_top:
    #   y_building_top = stack_y_top - sealing_height - building_height
    #   y_sealing_top  = stack_y_top - sealing_height
    #   y_ground_level = stack_y_top   (= top of topsoil)
    return {
        "available": bool(rendered_layers),
        "stack_x": stack_x,
        "stack_y_top": stack_y_top,
        "stack_width": stack_width,
        "stack_height": stack_height,
        "depth_m": depth_m,
        "layers": rendered_layers,
        "depth_ticks": depth_ticks,
        "groundwater_y": groundwater_y,
        "groundwater_depth_m": groundwater,
        "has_building": has_building,
        "building_height": building_height,
        "building_y": (
            stack_y_top - sealing_height - building_height
            if has_building else None
        ),
        "sealing_pct": sealing_pct,
        "sealing_height": sealing_height,
        "sealing_y": stack_y_top - sealing_height if sealing_height else None,
        "colors": {
            "bebauung": bebauung_color,
            "versiegelung": versiegelung_color,
            "groundwater": groundwater_color,
        },
    }


# ---------------------------------------------------------------------------
# Correlation radar — Komponente 5
# ---------------------------------------------------------------------------

def build_radar_render_context(
    component: dict,
    cx: int = 340,
    cy: int = 240,
    radius_max: int = 150,
) -> dict:
    """Project the 6-axis radar onto pixel space.

    Six fixed angles (top, top-right, bottom-right, bottom, bottom-left,
    top-left) at -90°, -30°, 30°, 90°, 150°, 210° — in SVG y-down
    convention.
    """
    axes_in = component.get("axes") or []
    # Six fixed angles in radians
    angles = [-math.pi / 2 + i * math.pi / 3 for i in range(6)]

    # Helper: position a point at given (axis, value 0..5)
    def point_at(axis_index: int, value: float) -> tuple[float, float]:
        a = angles[axis_index]
        r = (value / 5.0) * radius_max
        return cx + r * math.cos(a), cy + r * math.sin(a)

    rendered_axes: list[dict] = []
    polygon_pts: list[tuple[float, float]] = []
    polygon_dots: list[dict] = []
    has_any_value = False
    for i, axis in enumerate(axes_in[:6]):
        value = axis.get("value")
        # Label position just outside the outer ring
        a = angles[i]
        outer_x = cx + (radius_max + 18) * math.cos(a)
        outer_y = cy + (radius_max + 18) * math.sin(a)
        # Pick text-anchor based on which side of the centre
        if abs(math.cos(a)) < 0.2:
            anchor = "middle"
        elif math.cos(a) > 0:
            anchor = "start"
        else:
            anchor = "end"
        rendered_axes.append({
            "name": axis.get("name"),
            "label": axis.get("label", ""),
            "value": value,
            "raw_value": axis.get("raw_value", ""),
            "unit": axis.get("unit", ""),
            "label_x": outer_x,
            "label_y": outer_y,
            "value_y": outer_y + 14,
            "anchor": anchor,
            "axis_end": (cx + radius_max * math.cos(a), cy + radius_max * math.sin(a)),
        })
        if value is None:
            continue
        has_any_value = True
        try:
            v = max(0.0, min(5.0, float(value)))
        except (TypeError, ValueError):
            continue
        x, y = point_at(i, v)
        polygon_pts.append((x, y))
        polygon_dots.append({"cx": x, "cy": y})

    # Concentric hexagons (5 levels of the 0-5 scale)
    rings: list[str] = []
    for level in (1, 2, 3, 4, 5):
        pts = []
        for i in range(6):
            a = angles[i]
            r = (level / 5.0) * radius_max
            pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
        rings.append(" ".join(pts))

    polygon_str = (
        " ".join(f"{x:.1f},{y:.1f}" for x, y in polygon_pts)
        if len(polygon_pts) >= 3 else None
    )

    return {
        "available": has_any_value,
        "cx": cx,
        "cy": cy,
        "radius_max": radius_max,
        "rings": rings,
        "axes": rendered_axes,
        "polygon": polygon_str,
        "polygon_dots": polygon_dots,
        "dominant_driver": component.get("dominant_driver"),
        "interpretation": component.get("interpretation", ""),
        "correlation_r": component.get("correlation_coefficient"),
    }


# ---------------------------------------------------------------------------
# Neighborhood histogram — Komponente 6
# ---------------------------------------------------------------------------

def build_histogram_render_context(
    component: dict,
    tokens: Optional[dict] = None,
    chart_x: int = 60,
    chart_y_top: int = 80,
    chart_width: int = 580,
    chart_height: int = 140,
) -> dict:
    bins = component.get("bins") or []
    own_velocity = component.get("own_velocity")
    psi_count = component.get("psi_count", 0)

    if tokens:
        bands = tokens["ampel"]
        edge = tokens["ampel_edge"]
    else:
        bands = {
            "stabil":      {"color": "#1D9E75"},
            "leicht":      {"color": "#5DCAA5"},
            "moderat":     {"color": "#EF9F27"},
            "auffaellig":  {"color": "#E24B4A"},
            "erheblich":   {"color": "#A32D2D"},
            "kritisch":    {"color": "#A32D2D"},
        }
        edge = {"color": "#9FE1CB"}

    def color_for_velocity(v: float) -> str:
        # Histogram bin midpoints fall on half-integers (e.g. -0.5, 0.5, 1.5).
        # Map to the band that captures the bin's worst-case (|v| at the bin's
        # outer edge) so the central 1-mm bins (-1, 0) and (0, 1) read as
        # "stabil" rather than the transition shade.
        av = abs(v)
        if av <= 1.0:
            return bands["stabil"]["color"]
        if av <= 1.5:
            return edge["color"]  # "sehr leicht" transition shade
        if av <= 2.5:
            return bands["leicht"]["color"]
        if av <= 3.5:
            return bands["moderat"]["color"]
        if av <= 5.0:
            return bands["auffaellig"]["color"]
        return bands["erheblich"]["color"]

    # X-axis spans -5 to +5 mm/yr
    x_min, x_max = -5.0, 5.0

    def x_for_v(v: float) -> float:
        return chart_x + (v - x_min) / (x_max - x_min) * chart_width

    # Bar height based on max count
    counts = [int(b.get("count", 0)) for b in bins]
    max_count = max(counts) if counts else 0
    bar_h_max = chart_height - 10  # leave headroom for marker
    rendered_bars: list[dict] = []
    for b in bins:
        try:
            v_min = float(b["min"])
            v_max = float(b["max"])
            count = int(b["count"])
        except (KeyError, ValueError, TypeError):
            continue
        if count <= 0:
            continue
        x1 = x_for_v(v_min)
        x2 = x_for_v(v_max)
        h = (count / max_count) * bar_h_max if max_count else 0
        v_mid = (v_min + v_max) / 2.0
        rendered_bars.append({
            "x": x1 + 1,
            "y": chart_y_top + chart_height - h,
            "w": max(2.0, x2 - x1 - 2),
            "h": h,
            "fill": color_for_velocity(v_mid),
            "count": count,
            "v_min": v_min,
            "v_max": v_max,
        })

    # Marker for own velocity
    own_x = None
    if own_velocity is not None:
        try:
            v = float(own_velocity)
            v = max(x_min, min(x_max, v))
            own_x = x_for_v(v)
        except (TypeError, ValueError):
            pass

    # X-axis ticks at -5, -2.5, 0, +2.5, +5 plus own
    x_ticks = [
        {"value": -5.0, "label": "−5", "x": x_for_v(-5)},
        {"value": -2.5, "label": "−2.5", "x": x_for_v(-2.5)},
        {"value": 0.0, "label": "0", "x": x_for_v(0)},
        {"value": 2.5, "label": "+2.5", "x": x_for_v(2.5)},
        {"value": 5.0, "label": "+5", "x": x_for_v(5)},
    ]

    return {
        "available": bool(rendered_bars),
        "chart_x": chart_x,
        "chart_y_top": chart_y_top,
        "chart_width": chart_width,
        "chart_height": chart_height,
        "bars": rendered_bars,
        "x_ticks": x_ticks,
        "own_x": own_x,
        "own_velocity": own_velocity,
        "psi_count": psi_count,
        "percentile": component.get("percentile"),
        "interpretation": component.get("interpretation", ""),
    }
