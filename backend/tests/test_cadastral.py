"""Tests für app.cadastral — INSPIRE Cadastral Parcels Lookup.

Wir testen die generische Query-Logik + das State-Name-Mapping. Live-WFS-
Calls werden NICHT in CI gemacht (würde gegen Behörden-Server laufen) —
das macht der Operator beim Deploy via scripts/check-cadastral-wfs.sh.
"""

from __future__ import annotations

import pytest

from app.cadastral import (
    BUNDESLAND_ENDPOINTS,
    map_state_to_bundesland_code,
    _bbox_around_point,
)


def test_all_16_bundeslaender_in_lookup() -> None:
    """Alle 16 BL müssen einen Eintrag haben — auch wenn pending-license."""
    expected_codes = {
        "NW", "BE", "HH", "SN", "TH", "BB", "MV", "SH",
        "RP", "SL", "ST", "HB", "BY", "BW", "HE", "NI",
    }
    assert set(BUNDESLAND_ENDPOINTS.keys()) == expected_codes


@pytest.mark.parametrize(
    "code, expected_license",
    [
        # Phase 1a: Live-verifiziert HTTP 200 am 2026-05-06
        ("NW", "dl-de/by-2.0"),
        ("BE", "dl-de/by-2.0"),
        ("BB", "dl-de/by-2.0"),
        # Phase 1b: URL-Drift, Live-Test failed
        ("HH", "url-broken"),
        ("SN", "url-broken"),
        ("TH", "url-broken"),
        ("MV", "url-broken"),
        ("SH", "url-broken"),
        ("RP", "url-broken"),
        ("SL", "url-broken"),
        ("ST", "url-broken"),
        ("HB", "url-broken"),
        # Phase 2: Lizenz-Klärung läuft per Mail
        ("BY", "pending-license"),
        ("BW", "pending-license"),
        ("HE", "pending-license"),
        ("NI", "pending-license"),
    ],
)
def test_license_status_per_bundesland(code: str, expected_license: str) -> None:
    assert BUNDESLAND_ENDPOINTS[code]["license"] == expected_license


def test_phase1a_bundeslaender_have_live_urls() -> None:
    """Phase-1a-BL müssen produktive URLs haben (live-verifiziert HTTP 200)."""
    phase1a = {"NW", "BE", "BB"}
    for code in phase1a:
        url = BUNDESLAND_ENDPOINTS[code]["url"]
        assert url.startswith("https://"), f"{code} URL ist nicht produktiv: {url}"
        assert BUNDESLAND_ENDPOINTS[code]["license"] != "url-broken"


def test_phase2_bundeslaender_have_tbd_urls() -> None:
    """Phase-2-BL müssen TBD-Marker tragen damit query_cadastral früh None liefert."""
    phase2 = {"BY", "BW", "HE", "NI"}
    for code in phase2:
        assert BUNDESLAND_ENDPOINTS[code]["url"].startswith("TBD")


def test_url_broken_bundeslaender_skip_query() -> None:
    """url-broken-BL haben URLs (für späteren Refresh), aber license blockt query."""
    phase1b = {"HH", "SN", "TH", "MV", "SH", "RP", "SL", "ST", "HB"}
    for code in phase1b:
        assert BUNDESLAND_ENDPOINTS[code]["license"] == "url-broken"
        # URL bleibt drin damit man weiß welche Quelle gemeint war —
        # query_cadastral filtert per license-Status, nicht per URL
        assert BUNDESLAND_ENDPOINTS[code]["url"].startswith("https://")


@pytest.mark.parametrize(
    "name, expected",
    [
        ("Nordrhein-Westfalen", "NW"),
        ("Berlin", "BE"),
        ("Hamburg", "HH"),
        ("Sachsen", "SN"),
        ("Thüringen", "TH"),
        ("Brandenburg", "BB"),
        ("Mecklenburg-Vorpommern", "MV"),
        ("Schleswig-Holstein", "SH"),
        ("Rheinland-Pfalz", "RP"),
        ("Saarland", "SL"),
        ("Sachsen-Anhalt", "ST"),
        ("Bremen", "HB"),
        ("Bayern", "BY"),
        ("Baden-Württemberg", "BW"),
        ("Hessen", "HE"),
        ("Niedersachsen", "NI"),
    ],
)
def test_state_name_to_code_mapping(name: str, expected: str) -> None:
    assert map_state_to_bundesland_code(name) == expected


def test_state_name_unknown_returns_none() -> None:
    assert map_state_to_bundesland_code("Wakanda") is None
    assert map_state_to_bundesland_code(None) is None
    assert map_state_to_bundesland_code("") is None


def test_bbox_format() -> None:
    """WFS-BBox muss ``minLat,minLon,maxLat,maxLon,CRS``-Format haben."""
    bbox = _bbox_around_point(52.5, 13.4)
    parts = bbox.split(",")
    assert len(parts) == 5
    assert parts[4] == "EPSG:4326"
    # Halbedge sollte ~22m sein (= 0.0002 deg)
    assert abs(float(parts[0]) - 52.4998) < 1e-6
    assert abs(float(parts[2]) - 52.5002) < 1e-6


def test_attribution_present_for_all() -> None:
    """Jeder Eintrag braucht eine Attribution für den PDF-Footer."""
    for code, ep in BUNDESLAND_ENDPOINTS.items():
        assert ep["attribution"], f"{code} ohne Attribution"
        assert "©" in ep["attribution"], f"{code} Attribution ohne ©"
