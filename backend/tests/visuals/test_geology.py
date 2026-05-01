"""Tests for backend.app.geology — BGR GÜK250 lookup.

Live integration tests are marked ``live`` and skipped by default. Run
with ``pytest -m live`` to hit the real BGR endpoint.

Plan V.0.3 acceptance criterion: smoke-test against live endpoint at
the Schulstraße 12 (Gaggenau) coordinates yields a populated result.
"""

from __future__ import annotations

import pytest

from app.geology import (
    DE_BBOX,
    GeologyResult,
    _derive_risks,
    _in_germany,
    _parse_identify_response,
    query_geology,
)


def test_in_germany_includes_gaggenau() -> None:
    # Schulstraße 12, 76571 Gaggenau
    assert _in_germany(48.80123, 8.32456)


def test_in_germany_excludes_amsterdam() -> None:
    assert not _in_germany(52.37, 4.89)


def test_in_germany_excludes_paris() -> None:
    assert not _in_germany(48.85, 2.35)


# Note: Zurich (47.37°N) is geographically inside any sensible Germany
# bounding box because Germany's southernmost point (Oberstdorf, 47.27°N)
# is south of Zurich. The country_code gate is the real DE-only filter;
# the bbox is just a coarse sanity check.


def test_de_bbox_is_a_sensible_envelope() -> None:
    lon_min, lat_min, lon_max, lat_max = DE_BBOX
    assert lon_min < lon_max
    assert lat_min < lat_max
    # Sanity: must include Berlin, München, Hamburg, Saarbrücken
    assert _in_germany(52.52, 13.40)
    assert _in_germany(48.14, 11.58)
    assert _in_germany(53.55, 9.99)
    assert _in_germany(49.24, 6.99)


@pytest.mark.asyncio
async def test_query_geology_outside_germany_returns_unavailable() -> None:
    out = await query_geology(52.37, 4.89, country_code="nl")
    assert out["available"] is False
    assert "Deutschland" in out["note"]


@pytest.mark.asyncio
async def test_query_geology_de_country_outside_bbox_returns_unavailable() -> None:
    # de country code but coords in the Atlantic
    out = await query_geology(50.0, -2.0, country_code="de")
    assert out["available"] is False
    assert "Abdeckung" in out["note"]


def test_parse_identify_response_with_schulstrasse_12_payload() -> None:
    """Parser test using the actual BGR response shape recorded
    2026-05-01 for Schulstraße 12, 76571 Gaggenau.
    """
    payload = {
        "results": [
            {
                "layerId": 5,
                "layerName": "guek250_Basislayer_Stratigraphie",
                "attributes": {
                    "OBJECTID": "148215",
                    "Stratigraphie - gesamt": "Holozän",
                    "Stratigraphie - Anfang": "Holozän",
                    "Legendentext": "Holozän",
                },
            },
            {
                "layerId": 8,
                "layerName": "guek250_Basislayer_Petrographie",
                "attributes": {
                    "OBJECTID": "148215",
                    "Petrographie - kurz": "Ton bis Schluff, Sand, Kies",
                    "Petrographie - komplett": (
                        "Ton bis Schluff, vorwiegend sandig, teilweise humos, "
                        "Sand, Kies, selten Blöcke"
                    ),
                    "Legendentext": (
                        "Pelitisches Lockergestein, Psammitisches Lockergestein, "
                        "Psephitisches Lockergestein"
                    ),
                },
            },
        ]
    }
    result = _parse_identify_response(payload)
    assert result is not None
    assert result.available is True
    assert result.stratigraphy == "Holozän"
    assert result.stratigraphy_age == "Holozän"
    assert "Ton" in result.rock_type
    assert "Sand" in result.rock_type_short
    assert result.data_provenance is not None
    assert result.data_provenance["source"] == "BGR GÜK250"
    # Rock type contains Ton + humos → triggers two risks
    assert any("Quell" in r for r in result.risks)
    assert any("Setzungspotenzial" in r for r in result.risks)


def test_parse_identify_response_returns_none_on_empty_results() -> None:
    assert _parse_identify_response({"results": []}) is None
    assert _parse_identify_response({}) is None


def test_derive_risks_picks_up_clay() -> None:
    risks = _derive_risks("Pelitisches Lockergestein, Tonstein, Mergel")
    assert any("Quell" in r for r in risks)


def test_derive_risks_picks_up_peat() -> None:
    risks = _derive_risks("Niedermoortorf, organische Sedimente")
    assert any("Setzungspotenzial" in r for r in risks)


def test_derive_risks_picks_up_karst() -> None:
    risks = _derive_risks("Massenkalk, Karstgebiet")
    assert any("Karst" in r for r in risks)


def test_geology_result_to_dict_drops_none_fields() -> None:
    r = GeologyResult(available=False, source="BGR GÜK250", note="Test")
    d = r.to_dict()
    assert "rock_type" not in d
    assert "risks" not in d
    assert d["available"] is False
    assert d["note"] == "Test"


# ---------------------------------------------------------------------------
# Live integration test — hits the real BGR endpoint. Skipped by default.
# Run with: pytest -m live tests/visuals/test_geology.py
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytest.mark.asyncio
async def test_live_query_schulstrasse_12() -> None:
    """V.0.3 acceptance: live smoke test against BGR GÜK250."""
    out = await query_geology(48.80123, 8.32456, country_code="de", timeout=20.0)
    assert out["available"] is True, out
    assert out["source"].startswith("BGR GÜK250")
    # Gaggenau sits in Murg-Aue Holozän — expect Holozän stratigraphy
    assert "Holozän" in (out.get("stratigraphy") or "")
    assert out["data_provenance"]["source"] == "BGR GÜK250"
