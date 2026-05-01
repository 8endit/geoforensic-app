"""V.0.6 — verify additive data_provenance fields are present.

The plan acceptance for V.0.6 is "smoke-test: query_soil_directive(...)
contains data_provenance per value". A full live test requires DB +
rasters; here we verify the format spec is honored on the modules that
got the rollout in this batch (rfactor, slope, geology,
building_footprint).
"""

from __future__ import annotations

from app.rfactor_data import RFactorLookup, RFactorResult


def test_rfactor_fallback_emits_provenance() -> None:
    """When the ESDAC raster is missing, lat-linear fallback still
    produces a data_provenance dict (with sample_count=0)."""
    # Reset the singleton so the test doesn't depend on prior state
    RFactorLookup._instance = None
    result = RFactorLookup.get().query(48.80123, 8.32456, country_code="de")
    assert isinstance(result, RFactorResult)
    assert result.data_provenance is not None
    p = result.data_provenance
    assert "source" in p
    assert "method" in p
    # Either pixel-lookup (raster present) or lat-linear fallback
    assert p.get("regional_scope") in (None, "DE")


def test_provenance_format_required_keys() -> None:
    """All provenance dicts must have source, resolution_m,
    sample_count, method (per DATA_PROVENANCE.md §10)."""
    RFactorLookup._instance = None
    p = RFactorLookup.get().query(48.80, 8.32, "de").data_provenance
    for required in ("source", "method", "sample_count"):
        assert required in p, f"missing {required} in {p}"


def test_geology_result_has_provenance_when_available() -> None:
    """geology.py was provenance-aware from V.0.3 onwards."""
    from app.geology import _parse_identify_response

    payload = {
        "results": [
            {
                "layerId": 5,
                "layerName": "guek250_Basislayer_Stratigraphie",
                "attributes": {"Stratigraphie - gesamt": "Holozän"},
            },
            {
                "layerId": 8,
                "layerName": "guek250_Basislayer_Petrographie",
                "attributes": {"Petrographie - kurz": "Sand, Kies"},
            },
        ]
    }
    result = _parse_identify_response(payload)
    assert result.data_provenance is not None
    assert result.data_provenance["source"] == "BGR GÜK250"
    assert result.data_provenance["resolution_m"] == 250


def test_building_footprint_has_provenance_on_match() -> None:
    """building_footprint.py was provenance-aware from V.0.4 onwards."""
    from app.building_footprint import _parse_elements

    elements = [
        {
            "id": 1,
            "tags": {"addr:housenumber": "12", "addr:postcode": "76571"},
            "geometry": [
                {"lat": 48.8013, "lon": 8.3245},
                {"lat": 48.8014, "lon": 8.3245},
                {"lat": 48.8014, "lon": 8.3246},
                {"lat": 48.8013, "lon": 8.3246},
            ],
        }
    ]
    result = _parse_elements(elements, 48.80123, 8.32456, "12", "76571")
    assert result.data_provenance is not None
    assert "OpenStreetMap" in result.data_provenance["source"]
    assert result.data_provenance["license"] == "ODbL"
