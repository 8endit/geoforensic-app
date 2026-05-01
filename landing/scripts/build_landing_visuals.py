"""Pre-render the 6 Visuals as static SVG files for the landing page.

Renders each visual once with a real Berlin demo address (so the map
shows recognizable urban morphology from CartoDB Positron tiles) and
writes the result to ``landing/static/visuals/*.svg``. The landing
page embeds these via ``<img>`` so the browser doesn't run backend code.

Run::

    python -m landing.scripts.build_landing_visuals

The script is idempotent — running it again rewrites all six files
with fresh output. Call it after any backend visual-template change.

Note: the map fetch hits CartoDB tiles live the first run; subsequent
runs use the on-disk tile-cache (RASTER_DIR/tile_cache). Pass
``--no-basemap`` to force the offline grey-fallback mode.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make the backend modules importable when this script is run directly
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.basemap import build_map_render_context, fetch_basemap  # noqa: E402
from app.chart_helpers import (  # noqa: E402
    build_histogram_render_context,
    build_radar_render_context,
    build_soil_stack_render_context,
    build_timeseries_render_context,
)
from app.visual_payload import build_payload  # noqa: E402
from app.visual_renderer import load_tokens, render_svg  # noqa: E402

EXAMPLE_PAYLOAD = REPO_ROOT / "docs" / "visuals" / "example_payload.json"
OUT_DIR = REPO_ROOT / "landing" / "static" / "visuals"

# ---------------------------------------------------------------------------
# Demo address — Berlin Charlottenburg, dense urban grid, recognizable on
# CartoDB Positron tiles. Picked for landing-page basemap quality, not a
# real customer address.
# ---------------------------------------------------------------------------
DEMO_ADDRESS = {
    "full": "Bismarckstraße 10, 10625 Berlin",
    "street": "Bismarckstraße 10",
    "postcode": "10625",
    "city": "Berlin",
    "lat": 52.5142,
    "lon": 13.3145,
}


def _build_berlin_psi_points() -> list[dict]:
    """Generate 32 deterministic PSI points clustered tightly around
    the Berlin demo address (within 220 m). Compactness is deliberate:
    the landing-page demo zooms to ~250 m radius so the building is
    prominent — wider PSI scatter would land outside the visible map.

    The 3 nearest cluster at -0.4 to -0.6 mm/yr → 3-nearest mean ≈
    -0.5 → Burland Class 2 ‘leicht’; the rest are mostly ‘stabil’ so
    the histogram puts the address near the centre of the band, not
    the upper edge.
    """
    import math
    import random

    rnd = random.Random(20260501)
    lat0, lon0 = DEMO_ADDRESS["lat"], DEMO_ADDRESS["lon"]

    dpm_lat = 1.0 / 111_320.0
    dpm_lon = 1.0 / (111_320.0 * math.cos(math.radians(lat0)))

    points: list[dict] = []

    # 3 closest PSI points (~10-20 m from address). Velocities chosen
    # so the 3-nearest mean is ≈ -0.5 mm/yr (Class 2 ‘leicht’).
    for offset_m, velocity in [
        ((10, 8), -0.4),
        ((-12, 6), -0.5),
        ((4, -16), -0.6),
    ]:
        dx_m, dy_m = offset_m
        points.append({
            "lat": lat0 + dy_m * dpm_lat,
            "lon": lon0 + dx_m * dpm_lon,
            "velocity": velocity,
            "coherence": round(rnd.uniform(0.86, 0.92), 2),
        })

    # 29 further points scattered up to 220 m. Bulk slightly more
    # negative (-0.5 ± 0.4) so the address velocity (-0.5 from the
    # 3-nearest aggregate) lands close to the histogram centre rather
    # than upper-percentile.
    for _ in range(29):
        angle = rnd.uniform(0, 2 * math.pi)
        radius_m = rnd.uniform(35, 220)
        dx_m = math.cos(angle) * radius_m
        dy_m = math.sin(angle) * radius_m

        v = rnd.gauss(-0.5, 0.4)
        if rnd.random() < 0.10:
            v = rnd.uniform(-1.3, -0.9) if rnd.random() < 0.6 else rnd.uniform(0.3, 0.8)
        v = max(-1.3, min(0.9, v))

        points.append({
            "lat": lat0 + dy_m * dpm_lat,
            "lon": lon0 + dx_m * dpm_lon,
            "velocity": round(v, 2),
            "coherence": round(rnd.uniform(0.78, 0.92), 2),
        })

    return points


def _build_berlin_timeseries() -> tuple[list[dict], list[dict]]:
    """Build a 10-quarter PSI timeseries with a flat slope and seasonal
    residual that correlates with precipitation. Result: detrended
    Pearson r ≈ +0.55, consistent with ‘saisonal-getrieben’ in the
    correlation-radar interpretation."""
    import math
    import random

    rnd = random.Random(20260502)
    quarters = [
        (2020, 1), (2020, 7), (2021, 1), (2021, 7), (2022, 1),
        (2022, 7), (2023, 1), (2023, 7), (2024, 1), (2024, 7),
    ]
    # Berlin Q1/Q3 precipitation pattern: winter wet, summer dry.
    precip_pattern = [62, 38, 58, 42, 70, 35, 65, 48, 55, 40]

    psi_series: list[dict] = []
    precip_series: list[dict] = []
    cumulative = 0.0
    slope_per_quarter = -0.10  # ≈ -0.4 mm/yr long-term trend
    for i, ((year, month), mm) in enumerate(zip(quarters, precip_pattern)):
        # Seasonal residual mirrors precipitation (clay swelling under
        # wet winters → small heave; dry summers → small subsidence)
        seasonal = (mm - 50) * 0.012  # +0.24 mm at 70 mm, -0.24 mm at 30 mm
        noise = rnd.gauss(0, 0.05)
        cumulative += slope_per_quarter
        displacement = round(cumulative + seasonal + noise, 2)
        psi_series.append({
            "date": f"{year:04d}-{month:02d}-01",
            "displacement_mm": displacement,
        })
        precip_series.append({
            "date": f"{year:04d}-{month:02d}-01",
            "mm": mm,
        })
    return psi_series, precip_series


def _build_berlin_building_footprint() -> dict:
    """Synthesise a small Charlottenburg-style residential building
    footprint (~16 m × 11 m) centred on the address."""
    import math
    lat0, lon0 = DEMO_ADDRESS["lat"], DEMO_ADDRESS["lon"]
    dpm_lat = 1.0 / 111_320.0
    dpm_lon = 1.0 / (111_320.0 * math.cos(math.radians(lat0)))
    half_w = 8 * dpm_lon  # 16 m wide
    half_h = 5.5 * dpm_lat  # 11 m deep
    polygon = [
        [lon0 - half_w, lat0 - half_h],
        [lon0 + half_w, lat0 - half_h],
        [lon0 + half_w, lat0 + half_h],
        [lon0 - half_w, lat0 + half_h],
    ]
    return {
        "available": True,
        "polygon": polygon,
        "centroid": [lon0, lat0],
    }


def _berlin_soil_layers() -> list[dict]:
    """Berlin Charlottenburg-typical glacial-sediment column."""
    return [
        {
            "type": "topsoil",
            "depth_top_m": 0.0, "depth_bottom_m": 0.4,
            "label": "Mutterboden",
            "source": "SoilGrids 250 m",
            "soc_percent": 1.4, "ph": 6.2,
        },
        {
            "type": "subsoil",
            "depth_top_m": 0.4, "depth_bottom_m": 1.8,
            "label": "Sand, kiesig",
            "source": "BGR GÜK250 — Holozän",
        },
        {
            "type": "weathered",
            "depth_top_m": 1.8, "depth_bottom_m": 3.5,
            "label": "Geschiebemergel",
            "source": "BGR GÜK250 — Pleistozän",
        },
        {
            "type": "bedrock",
            "depth_top_m": 3.5, "depth_bottom_m": 5.0,
            "label": "Glaziale Sedimente",
            "source": "BGR GÜK250 — Saale-Kaltzeit",
        },
    ]


def _build_demo_payload() -> dict:
    psi_points = _build_berlin_psi_points()
    psi_series, precip_series = _build_berlin_timeseries()
    building = _build_berlin_building_footprint()
    soil_layers = _berlin_soil_layers()

    return build_payload(
        address=DEMO_ADDRESS,
        psi_points=psi_points,
        psi_timeseries=psi_series,
        precipitation_series=precip_series,
        annual_precipitation_mm=590,  # Berlin DWD long-term mean
        sealing_percent=65,           # Charlottenburg block density
        clay_percent=12,              # sandy Berlin substrate
        slope_degrees=0.5,            # flat
        groundwater_depth_m=-7.5,     # typical Charlottenburg
        soil_layers=soil_layers,
        building_footprint=building,
        radius_meters=250,            # closer zoom for landing demo
        tier="premium",
        report_id="GF-DEMO-LANDING",
    )


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    use_basemap = "--no-basemap" not in sys.argv

    payload = _build_demo_payload()
    components = payload["components"]
    tokens = load_tokens()

    # Tier-1
    rd_svg = render_svg("risk_dashboard", components["risk_dashboard"])

    basemap = None
    if use_basemap:
        print("  fetching CartoDB Positron tiles for "
              f"{DEMO_ADDRESS['full']} ({DEMO_ADDRESS['lat']:.4f}, "
              f"{DEMO_ADDRESS['lon']:.4f}) ...")
        basemap = fetch_basemap(
            DEMO_ADDRESS["lat"], DEMO_ADDRESS["lon"],
            radius_m=250, width_px=600, height_px=320,
        )
        if basemap.get("available"):
            print(f"  basemap z={basemap['zoom']}, "
                  f"{len(basemap['image_data_uri']) // 1024} KB inline PNG")
        else:
            print(f"  basemap fetch failed: {basemap.get('note')}")

    map_ctx = build_map_render_context(
        components["property_context_map"],
        address_lat=payload["address"]["lat"],
        address_lon=payload["address"]["lon"],
        basemap=basemap,
        tokens=tokens,
    )
    map_svg = render_svg(
        "property_context_map", components["property_context_map"], map=map_ctx
    )

    # Tier-2
    ts_ctx = build_timeseries_render_context(components["velocity_timeseries"])
    ts_svg = render_svg("velocity_timeseries", components["velocity_timeseries"], chart=ts_ctx)
    soil_ctx = build_soil_stack_render_context(components["soil_context_stack"], tokens=tokens)
    soil_svg = render_svg("soil_context_stack", components["soil_context_stack"], stack=soil_ctx)
    radar_ctx = build_radar_render_context(components["correlation_radar"])
    radar_svg = render_svg("correlation_radar", components["correlation_radar"], radar=radar_ctx)
    hist_ctx = build_histogram_render_context(
        components["neighborhood_histogram"], tokens=tokens,
    )
    hist_svg = render_svg(
        "neighborhood_histogram", components["neighborhood_histogram"], hist=hist_ctx,
    )

    pairs = [
        ("01_risk_dashboard.svg", rd_svg),
        ("02_property_context_map.svg", map_svg),
        ("03_velocity_timeseries.svg", ts_svg),
        ("04_soil_context_stack.svg", soil_svg),
        ("05_correlation_radar.svg", radar_svg),
        ("06_neighborhood_histogram.svg", hist_svg),
    ]
    for name, svg in pairs:
        target = OUT_DIR / name
        target.write_text(svg, encoding="utf-8")
        size_kb = target.stat().st_size / 1024
        print(f"  {name:36s} {size_kb:6.1f} KB")

    print(f"Wrote {len(pairs)} SVGs to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
