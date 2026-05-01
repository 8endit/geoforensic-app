"""Tests for backend.app.building_footprint — OSM Overpass lookup."""

from __future__ import annotations

import pytest

from app.building_footprint import (
    _build_overpass_query,
    _haversine_m,
    _normalize_housenumber,
    _parse_elements,
    _polygon_centroid,
    query_building_footprint,
)


def test_haversine_zero_distance() -> None:
    assert _haversine_m(48.0, 8.0, 48.0, 8.0) == 0.0


def test_haversine_known_distance() -> None:
    # Berlin Brandenburger Tor (52.5163, 13.3777) to München Marienplatz (48.1374, 11.5755)
    # ≈ 504 km
    d = _haversine_m(52.5163, 13.3777, 48.1374, 11.5755)
    assert 500_000 < d < 510_000


def test_polygon_centroid_simple_square() -> None:
    coords = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    c = _polygon_centroid(coords)
    assert c == [0.5, 0.5]


def test_normalize_housenumber_strips_and_lowers() -> None:
    assert _normalize_housenumber("12 a") == "12a"
    assert _normalize_housenumber("12A") == "12a"
    assert _normalize_housenumber(" 12 ") == "12"
    assert _normalize_housenumber(None) is None
    assert _normalize_housenumber("") is None


def test_overpass_query_contains_radius_and_coords() -> None:
    q = _build_overpass_query(48.80123, 8.32456, 50)
    assert "around:50" in q
    assert "48.80123" in q
    assert "8.32456" in q
    assert "way[building]" in q


def test_parse_elements_picks_housenumber_match() -> None:
    elements = [
        {
            "id": 1,
            "tags": {"addr:housenumber": "11", "addr:postcode": "76571"},
            "geometry": [
                {"lat": 48.8011, "lon": 8.3241},
                {"lat": 48.8012, "lon": 8.3241},
                {"lat": 48.8012, "lon": 8.3242},
                {"lat": 48.8011, "lon": 8.3242},
            ],
        },
        {
            "id": 2,
            "tags": {"addr:housenumber": "12", "addr:postcode": "76571"},
            "geometry": [
                {"lat": 48.8013, "lon": 8.3245},
                {"lat": 48.8014, "lon": 8.3245},
                {"lat": 48.8014, "lon": 8.3246},
                {"lat": 48.8013, "lon": 8.3246},
            ],
        },
        {
            "id": 3,
            "tags": {"addr:housenumber": "13", "addr:postcode": "76571"},
            "geometry": [
                {"lat": 48.8015, "lon": 8.3248},
                {"lat": 48.8016, "lon": 8.3248},
                {"lat": 48.8016, "lon": 8.3249},
                {"lat": 48.8015, "lon": 8.3249},
            ],
        },
    ]
    result = _parse_elements(
        elements, 48.80123, 8.32456, housenumber="12", postcode="76571"
    )
    assert result is not None
    assert result.available is True
    assert result.osm_way_id == 2
    assert result.match_basis == "housenumber"
    assert result.data_provenance["source"].startswith("OpenStreetMap")


def test_parse_elements_falls_back_to_nearest() -> None:
    elements = [
        {
            "id": 1,
            "tags": {},
            "geometry": [
                {"lat": 48.80, "lon": 8.32},
                {"lat": 48.80, "lon": 8.321},
                {"lat": 48.801, "lon": 8.321},
                {"lat": 48.801, "lon": 8.32},
            ],
        },
        {
            "id": 2,
            "tags": {},
            "geometry": [
                {"lat": 48.8012, "lon": 8.3245},
                {"lat": 48.8012, "lon": 8.3246},
                {"lat": 48.8013, "lon": 8.3246},
                {"lat": 48.8013, "lon": 8.3245},
            ],
        },
    ]
    result = _parse_elements(elements, 48.80123, 8.32456, None, None)
    assert result is not None
    assert result.osm_way_id == 2  # the nearby one
    assert result.match_basis == "nearest"
    assert "Nächstgelegen" in result.note


def test_parse_elements_returns_none_on_empty_list() -> None:
    assert _parse_elements([], 48.0, 8.0, None, None) is None


def test_parse_elements_skips_degenerate_geometry() -> None:
    """Ways with fewer than 3 points cannot form polygons."""
    elements = [
        {"id": 1, "tags": {}, "geometry": [{"lat": 48.80, "lon": 8.32}]},
        {"id": 2, "tags": {}, "geometry": []},
    ]
    assert _parse_elements(elements, 48.80, 8.32, None, None) is None


def test_parse_elements_housenumber_match_requires_postcode_too() -> None:
    """Without postcode in the request, we fall through to nearest."""
    elements = [
        {
            "id": 1,
            "tags": {"addr:housenumber": "12"},  # no postcode
            "geometry": [
                {"lat": 48.8013, "lon": 8.3245},
                {"lat": 48.8014, "lon": 8.3245},
                {"lat": 48.8014, "lon": 8.3246},
                {"lat": 48.8013, "lon": 8.3246},
            ],
        },
    ]
    # postcode missing in request → housenumber match short-circuits, falls to nearest
    result = _parse_elements(elements, 48.80123, 8.32456, "12", None)
    assert result.match_basis == "nearest"


# ---------------------------------------------------------------------------
# Live integration test against Overpass — skipped by default.
# ---------------------------------------------------------------------------

@pytest.mark.live
async def test_live_query_schulstrasse_gaggenau() -> None:
    """V.0.4 acceptance: live Overpass query at Schulstraße 12 area."""
    out = await query_building_footprint(
        48.80123, 8.32456, housenumber="11", postcode="76571", radius_m=50
    )
    assert out["available"] is True, out
    assert out["polygon"] is not None
    assert len(out["polygon"]) >= 3
    # 11 exists in OSM at this location → expect housenumber match
    assert out["match_basis"] == "housenumber"
    assert out["data_provenance"]["source"].startswith("OpenStreetMap")


@pytest.mark.live
async def test_live_query_returns_unavailable_in_atlantic() -> None:
    """No buildings → available=False, no crash."""
    out = await query_building_footprint(50.0, -30.0, radius_m=50)
    assert out["available"] is False
