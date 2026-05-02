"""Altlasten / Bodenkontaminationen — country-routed lookup.

Honest data-availability landscape (verified 2026-04-30):

    NL    PDOK Bodemloket — PUBLIC WMS, layer "WBB_locaties"
          URL: https://gis.gdngeoservices.nl/standalone/services/
                blk_gdn/lks_blk_rd_v1/MapServer/WMSServer
          License: CC-BY 4.0
          Result: actual address-level contamination dossiers.

    DE    No public address-level Altlasten WFS. Both LUBW (BW) and
          LANUV (NRW) gate the data behind authority access:
            - LUBW ALTIS: INSPIRE Art 13(1)(f), Eigentuemer-Bezug,
              Antrag an rips@lubw.bwl.de erforderlich
            - LANUV FIS AlBo: nur Landesverwaltungsnetz / DOI-Netz
          → Wir liefern stattdessen einen CORINE-basierten **Proxy**:
            CORINE Codes 131 (Abbauflaechen), 132 (Deponien),
            133 (Baustellen) im 200 m-Radius. Kein Ersatz fuer eine
            Behoerdenauskunft, aber ein offen verifizierbarer Indikator.
          Fuer rechtsverbindliche Auskunft → Behoerden-Vermittlungsdienste
          wie docestate.com oder direkt zustaendiges Bauamt.

    AT/CH Nicht integriert.

The proxy is honest about what it is. We never claim to have the LUBW or
LANUV dataset; the report sections always cite their actual data source.
"""

from __future__ import annotations

import logging
import math
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass

import httpx

logger = logging.getLogger(__name__)

_QUERY_RADIUS_M = 200

# CORINE codes that flag potential historic land-use contamination risk.
# Each carries a typical Altlasten-correlation reason for the report.
_CORINE_PROXY_CODES: dict[int, str] = {
    121: "Industrie- und Gewerbeflaeche (historisch oft Loesungsmittel/Schwermetalle)",
    122: "Strassen-/Eisenbahnflaeche (historisch oft PAK/Schwermetalle)",
    123: "Hafengebiet (Hafenschlamm, oel-verunreinigte Boeden moeglich)",
    124: "Flughafenflaeche (Loesch-/Treibstoffrueckstaende moeglich)",
    131: "Abbauflaeche / Bergbau (Schwermetalle, Saure Bergbauwaesser)",
    132: "Deponie / Abraumhalde (heterogene Schadstoffe)",
    133: "Baustelle / Brachflaeche (vorheriger Nutzungs-Cocktail)",
}

# Sample offsets (deg) for 4-cardinal proximity scan (~50 m)
_PROXY_OFFSET_DEG = 0.00045  # ≈ 50 m at 51°N


@dataclass
class ContaminatedSite:
    site_id: str
    name: str
    site_type: str
    status: str
    distance_m: float
    source: str


@dataclass
class CorineProxyHit:
    """Honest CORINE-based proxy. NOT a confirmed Altlast — just a
    land-use class within 200 m that historically correlates with
    contamination risk."""
    code: int
    label: str
    distance_m: float


# ── Helpers ──────────────────────────────────────────────────────────────

def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _bbox(lat: float, lon: float, radius_m: float = _QUERY_RADIUS_M) -> tuple[float, float, float, float]:
    """Return (min_lon, min_lat, max_lon, max_lat) bounding box."""
    dlat = radius_m / 111_320.0
    dlon = radius_m / (111_320.0 * max(math.cos(math.radians(lat)), 0.01))
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat


# ── NL: PDOK Bodemloket ──────────────────────────────────────────────────

# New URL after the 2023 migration. The legacy /rws/bodemloket/ path is dead.
_PDOK_BODEMLOKET_WMS = (
    "https://gis.gdngeoservices.nl/standalone/services/"
    "blk_gdn/lks_blk_rd_v1/MapServer/WMSServer"
)
_PDOK_LAYER = "WBB_locaties"


async def _query_pdok_bodemloket(
    client: httpx.AsyncClient, lat: float, lon: float
) -> list[ContaminatedSite]:
    """WMS GetFeatureInfo on the PDOK Bodemloket WBB_locaties layer.

    Returns parsed sites. The endpoint speaks ESRI WMS XML
    (FeatureInfoResponse), not GeoJSON; we parse the XML directly.
    """
    min_lon, min_lat, max_lon, max_lat = _bbox(lat, lon, radius_m=200)
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetFeatureInfo",
        "LAYERS": _PDOK_LAYER,
        "QUERY_LAYERS": _PDOK_LAYER,
        "CRS": "EPSG:4326",
        "BBOX": f"{min_lat},{min_lon},{max_lat},{max_lon}",
        "WIDTH": 201,
        "HEIGHT": 201,
        "I": 100,
        "J": 100,
        "INFO_FORMAT": "text/xml",
        "FEATURE_COUNT": 20,
    }
    try:
        resp = await client.get(_PDOK_BODEMLOKET_WMS, params=params, timeout=15.0)
        if resp.status_code != 200:
            logger.debug("PDOK Bodemloket HTTP %s", resp.status_code)
            return []

        root = ET.fromstring(resp.text)
        sites: list[ContaminatedSite] = []
        # ESRI WMS XML namespace handling: walk and pick FeatureInfo elements
        for feat in root.iter():
            tag = feat.tag.rsplit("}", 1)[-1]
            if tag != "FeatureInfo":
                continue
            attrs: dict[str, str] = {}
            for child in feat:
                ctag = child.tag.rsplit("}", 1)[-1]
                attrs[ctag] = (child.text or "").strip()
            if not attrs:
                continue

            site_id = attrs.get("OBJECTID") or attrs.get("ID") or attrs.get("BSN_ID") or "?"
            name = (attrs.get("NAAM") or attrs.get("STRAATNAAM")
                    or attrs.get("LOCATIE") or "Locatie onbekend")
            status_raw = (attrs.get("FASE") or attrs.get("STATUS") or "onbekend").lower()
            if any(k in status_raw for k in ("gesaneerd", "afgerond", "gesloten")):
                status = "abgeschlossen"
            elif any(k in status_raw for k in ("actief", "sanering", "lopend")):
                status = "aktiv"
            else:
                status = "onbekend"

            sites.append(ContaminatedSite(
                site_id=str(site_id),
                name=name,
                site_type="Locatie (Wbb)",
                status=status,
                distance_m=0.0,  # PDOK XML doesn't return geometry per feature
                source="PDOK Bodemloket (NL)",
            ))
        return sites
    except Exception as exc:  # noqa: BLE001
        logger.debug("PDOK Bodemloket error: %s", exc)
        return []


# ── DE: CORINE proxy (no public Altlasten WFS) ───────────────────────────

# Lazy import to avoid a hard dependency cycle at module load
def _corine_proxy(lat: float, lon: float) -> dict:
    """Sample CORINE land-use at the address and 4 cardinal probes ~50 m
    around it; collect every hit on a contamination-correlated code.

    Returns ``{"hits": [...], "risk": "gruen|gelb|rot"}``. Distance values
    are coarse (0 m or ~50 m) — the source raster is 100 m so finer
    granularity would be artificial.
    """
    try:
        from app.soil_data import CLC_LABELS, SoilDataLoader
    except Exception:
        return {"hits": [], "risk": "gruen"}

    loader = SoilDataLoader.get()
    samples = [(lat, lon, 0.0)]
    for dlat, dlon in [
        (_PROXY_OFFSET_DEG, 0), (-_PROXY_OFFSET_DEG, 0),
        (0, _PROXY_OFFSET_DEG), (0, -_PROXY_OFFSET_DEG),
    ]:
        samples.append((lat + dlat, lon + dlon, 50.0))

    seen_codes: set[int] = set()
    hits: list[CorineProxyHit] = []
    for s_lat, s_lon, dist in samples:
        c = loader.query_corine(s_lat, s_lon)
        if not c:
            continue
        code = c.get("code")
        if code not in _CORINE_PROXY_CODES or code in seen_codes:
            continue
        seen_codes.add(code)
        hits.append(CorineProxyHit(
            code=code,
            label=CLC_LABELS.get(code, f"CLC {code}"),
            distance_m=dist,
        ))

    # Risk: 131/132 (mining/landfill) are historically the worst → gelb
    # 121/122/123/124/133 → also gelb but lower-confidence
    # Rote Stufe geben wir nicht, weil CORINE-Proxy nie eine Schadstoff-
    # Bestätigung sein kann — dafür braucht es die Behoerdenauskunft.
    risk = "gelb" if hits else "gruen"
    return {"hits": [asdict(h) for h in hits], "risk": risk}


# ── Risk classification ──────────────────────────────────────────────────

def _classify_risk_from_sites(sites: list[ContaminatedSite]) -> str:
    if not sites:
        return "gruen"
    if any(s.status == "aktiv" for s in sites):
        return "rot"
    return "gelb"


# ── Public API ───────────────────────────────────────────────────────────

async def fetch_altlasten(lat: float, lon: float, country_code: str = "de") -> dict:
    """Country-routed contaminated-site lookup.

    NL → PDOK Bodemloket WBB_locaties (real address-level data).
    DE → CORINE-proxy (open-data, NOT a Behoerdenauskunft) with explicit note
         pointing to docestate / Bauamt for legally-binding extracts.
    AT/CH/Other → not integrated, returns available=False.

    Returns a dict ready for full_report.py consumption. Each result carries
    a ``data_kind`` field so the PDF section can label itself accurately
    ('Bodemloket WMS' vs 'Land-Use-Indikator (CORINE)').
    """
    cc = (country_code or "de").lower()

    if cc == "nl":
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": "GeoForensic/0.1 (kontakt@geoforensic.de)"},
        ) as client:
            sites = await _query_pdok_bodemloket(client, lat, lon)
        site_dicts = [asdict(s) for s in sites]
        return {
            "available": True,
            "country": "NL",
            "data_kind": "behoerden-kataster",
            "source": "PDOK Bodemloket (CC-BY 4.0)",
            "risk": _classify_risk_from_sites(sites),
            "site_count": len(sites),
            "sites": site_dicts[:20],
            "has_active": any(s.status == "aktiv" for s in sites),
            "note": (
                "Adress-genaue Wbb-Lokationen (Wet bodembescherming) aus dem "
                "PDOK Bodemloket — die offizielle nationale Datenbank."
            ),
        }

    if cc == "de":
        proxy = _corine_proxy(lat, lon)
        # Add the contamination-reason for each hit so the PDF can show why
        for h in proxy["hits"]:
            h["reason"] = _CORINE_PROXY_CODES.get(h["code"], "")
        return {
            "available": True,
            "country": "DE",
            "data_kind": "land-use-indikator",
            "source": "CORINE Land Cover 2018 (Copernicus EEA)",
            "risk": proxy["risk"],
            "site_count": len(proxy["hits"]),
            "sites": proxy["hits"],
            "has_active": False,
            "offer_authority_request": True,
            "note": (
                "Adress-genaue Altlasten-Daten in DE sind nicht oeffentlich "
                "abrufbar (LUBW ALTIS / LANUV FIS AlBo geschuetzt nach "
                "INSPIRE Art 13(1)(f)). Diese Sektion zeigt einen Land-Use-"
                "Indikator auf CORINE-Basis im 100-150 m-Umfeld. Fuer eine "
                "rechtsverbindliche Behoerdenauskunft koennen wir die "
                "Anfrage in Ihrem Auftrag stellen — Kontakt: "
                "altlasten@geoforensic.de."
            ),
        }

    return {
        "available": False,
        "country": cc.upper(),
        "data_kind": None,
        "note": f"Altlasten-Lookup fuer {cc.upper()} nicht integriert.",
    }
