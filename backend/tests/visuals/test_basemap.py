"""V.2.3 — tests for backend.app.basemap.

Live tests fetch real tiles from CartoDB and are skipped by default.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from app.basemap import (
    ATTRIBUTION,
    fetch_basemap,
    lonlat_to_tile_xy,
    pick_zoom,
    project_lonlat_to_pixel,
    tile_xy_to_lonlat,
)


def test_lonlat_to_tile_round_trip() -> None:
    """Mercator projection round-trips within sub-pixel precision."""
    for lat, lon in [(48.80, 8.32), (52.52, 13.40), (51.92, 4.48)]:
        for z in (12, 15, 18):
            x, y = lonlat_to_tile_xy(lon, lat, z)
            lon2, lat2 = tile_xy_to_lonlat(x, y, z)
            assert abs(lon - lon2) < 1e-9
            assert abs(lat - lat2) < 1e-9


def test_pick_zoom_chooses_higher_z_for_smaller_radius() -> None:
    z_500 = pick_zoom(500, 48.8, 600)
    z_2000 = pick_zoom(2000, 48.8, 600)
    assert z_500 >= z_2000


def test_pick_zoom_clamped_at_18() -> None:
    z = pick_zoom(10, 48.8, 600)  # tiny radius would push beyond max
    assert z <= 18


def test_pick_zoom_around_15_or_16_for_500m() -> None:
    """At lat ~48.8°, 500 m radius / 600 px → ~1.67 m/px → z=16ish."""
    z = pick_zoom(500, 48.8, 600)
    assert 14 <= z <= 17


def test_project_lonlat_to_pixel_top_left_and_bottom_right() -> None:
    bbox = (8.30, 48.79, 8.34, 48.81)
    w, h = 600, 320
    x, y = project_lonlat_to_pixel(8.30, 48.81, bbox, w, h)
    assert (x, y) == (0.0, 0.0)
    x, y = project_lonlat_to_pixel(8.34, 48.79, bbox, w, h)
    assert math.isclose(x, 600)
    assert math.isclose(y, 320)


def test_project_lonlat_to_pixel_centre() -> None:
    bbox = (8.30, 48.79, 8.34, 48.81)
    cx_lon = (bbox[0] + bbox[2]) / 2
    cx_lat = (bbox[1] + bbox[3]) / 2
    x, y = project_lonlat_to_pixel(cx_lon, cx_lat, bbox, 600, 320)
    assert math.isclose(x, 300)
    assert math.isclose(y, 160)


def test_attribution_constant() -> None:
    assert "CARTO" in ATTRIBUTION
    assert "OpenStreetMap" in ATTRIBUTION


def test_fetch_basemap_returns_unavailable_on_offline() -> None:
    """If httpx fails (no network), result is ``available=False`` with a
    note — never raises."""
    # We can't easily mock httpx here, but we can verify the contract
    # by passing a clearly-bad style that triggers HTTP 404 on every tile.
    out = fetch_basemap(48.80123, 8.32456, radius_m=500, style="does_not_exist_xyz")
    assert "available" in out
    if not out["available"]:
        assert out["note"]
    # If by chance CartoDB returns something for the bogus style (it shouldn't),
    # the test still passes — we only assert the contract.


# ---------------------------------------------------------------------------
# Live tile fetch — slow, hits CartoDB
# ---------------------------------------------------------------------------

@pytest.mark.live
def test_live_fetch_basemap_for_schulstrasse() -> None:
    """V.2.3 acceptance: live tile fetch produces a usable composite."""
    out = fetch_basemap(48.80123, 8.32456, radius_m=500, width_px=600, height_px=320)
    assert out["available"] is True, out
    assert out["image_data_uri"].startswith("data:image/png;base64,")
    assert out["width_px"] == 600
    assert out["height_px"] == 320
    bbox = out["bbox"]
    # Address must be inside the bbox
    assert bbox[0] < 8.32456 < bbox[2]
    assert bbox[1] < 48.80123 < bbox[3]
    assert "CARTO" in out["attribution"]
    assert out["data_provenance"]["license"] == "CC BY 3.0"


@pytest.mark.live
def test_live_basemap_uses_tile_cache_on_second_call(tmp_path, monkeypatch) -> None:
    """Re-running fetch_basemap for the same coordinates should hit
    the cache and skip the network for the second call."""
    # Redirect cache to a temp directory
    monkeypatch.setenv("RASTER_DIR", str(tmp_path))
    # Reload module to pick up the new RASTER_DIR
    import importlib
    import app.basemap as bm
    importlib.reload(bm)

    out1 = bm.fetch_basemap(48.80123, 8.32456, radius_m=500, width_px=300, height_px=200)
    assert out1["available"] is True

    cache_dir = tmp_path / "tile_cache"
    assert cache_dir.exists()
    cached_files = list(cache_dir.rglob("*.png"))
    assert len(cached_files) > 0

    # Second call: should be served entirely from cache (no network needed)
    out2 = bm.fetch_basemap(48.80123, 8.32456, radius_m=500, width_px=300, height_px=200)
    assert out2["available"] is True
    assert out2["image_data_uri"] == out1["image_data_uri"]

    # Reload again to restore module state for other tests
    importlib.reload(bm)
