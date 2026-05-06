"""INSPIRE Cadastral Parcels WFS-Client — Adresse → Flurstück.

Sprint E1 (2026-05-06): Statt 500m-Radius um Adresse das jeweilige
Flurstück als räumliche Bezugseinheit nutzen. Damit werden kategoriale
Layer (Hochwasserzone, Bergbau-Berechtigung, Versiegelungsgrad)
parzellenscharf zuordbar — kontinuierliche Layer (EGMS, SoilGrids)
bleiben physikalisch gemittelt (Sentinel-1 misst auf 100m-Raster).

INSPIRE-Standard
----------------
Seit der EU-INSPIRE-Richtlinie 2007/2/EG müssen alle Bundesländer einen
WFS für ``cp:CadastralParcel`` (Cadastral Parcels, Annex I Theme 6)
bereitstellen. Datenmodell ist EU-standardisiert — eine Code-Pfad für
alle 16 Bundesländer, nur unterschiedliche Endpunkt-URLs.

Lizenz pro Bundesland (Stand 2026-05-06 Live-Test)
---------------------------------------------------
Phase 1a (3 BL, GetCapabilities live mit HTTP 200):
  NRW, Berlin, Brandenburg.

Phase 1b (9 BL, URL-Drift — bei letztem check-cadastral-wfs.sh-Lauf
HTTP 403/404/500). URLs müssen recherchiert werden via:
  - GDI-DE Geoportal-Suche (https://gdk.gdi-de.org/)
  - GetCapabilities-Antwort des jeweiligen Geoportal-Hauptdienstes
  - Direkte Anfrage an die LVG-Operations-Stelle
Aktuell als ``license="url-broken"`` markiert, query_cadastral
liefert für diese BL None und der Bericht fällt auf 500m-Radius
zurück.

Phase 2 (4 BL mit Lizenz-Klärung — Mails siehe docs/MAIL_INSPIRE_CADASTRAL.md):
  Bayern, Baden-Württemberg, Hessen, Niedersachsen.

Bei einer Adresse aus den Phase-1b/Phase-2-Bundesländern fällt das
Modul auf den 500m-Radius-Pfad zurück, mit Hinweis im Bericht.

URLs verifizieren!
------------------
Die Endpunkt-URLs in BUNDESLAND_ENDPOINTS sind Best-Effort-Stand 2024/2025.
Vor jedem Roll-out einmal mit ``GetCapabilities`` pro URL prüfen
(siehe scripts/check-cadastral-wfs.sh). Service-URLs ändern sich
gelegentlich nach Behörden-Reorganisation.
"""

from __future__ import annotations

import asyncio
import logging
import os
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "Bodenbericht/1.0 (kontakt@geoforensic.de)"

# CRS für die WFS-BBox-Anfrage. INSPIRE-Standard ist EPSG:4326 (WGS84,
# lat/lon). Manche Bundesländer akzeptieren auch UTM (EPSG:25832/25833),
# bevorzugen wir aber 4326 weil das auch unsere Geocode-Antwort ist.
_CRS = "EPSG:4326"
_BBOX_HALF_DEG = 0.0002  # ~22 m — klein genug, ein Flurstück trifft genau einen Match

_TIMEOUT_S = 10.0


@dataclass
class CadastralParcel:
    """Ein Flurstück, das eine gegebene Adresse enthält.

    Felder:
        bundesland: 2-Buchstaben-Code (BE, NW, HH, …)
        gemarkung: Gemarkungs-Name (z.B. "Bochum-Wattenscheid")
        flurstueck_nr: Zähler/Nenner-Notation (z.B. "3200/10")
        area_m2: Fläche in Quadratmetern
        polygon_wkt: Geometrie als WKT-String (für PostGIS-Cache)
        source_url: WFS-Endpunkt der die Antwort lieferte (Provenance)
        license: Lizenz-Kürzel (dl-de/by-2.0, dl-de/zero-2.0, …)
        attribution: Quellen-Text für PDF-Footer
    """
    bundesland: str
    gemarkung: Optional[str]
    flurstueck_nr: Optional[str]
    area_m2: Optional[float]
    polygon_wkt: Optional[str]
    source_url: str
    license: str
    attribution: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Bundesland-Endpunkte
# ---------------------------------------------------------------------------
#
# Format pro Eintrag:
#   url:        WFS-Service-URL (ohne Query-String)
#   typename:   Feature-Type — INSPIRE-Standard ist "cp:CadastralParcel",
#               einige BL nutzen abweichende Schemas (siehe Kommentar pro BL)
#   license:    dl-de/by-2.0 / dl-de/zero-2.0 / pending-license / commercial-required
#   attribution: für PDF-Footer (CC-BY-Pflicht bei dl-de/by-2.0)
#   notes:      Operative Notizen (CRS-Eigenheiten, Quoten, …)
#
# WICHTIG: Phase-1-URLs (license != "pending-license") können live laufen,
# Phase-2-URLs sind als Stubs drin und werfen `LicenseNotApprovedError`.

BUNDESLAND_ENDPOINTS: dict[str, dict[str, Any]] = {
    # ── Phase 1a — Live-verifiziert 2026-05-06, HTTP 200 ──────────────
    "NW": {  # Nordrhein-Westfalen
        "url": "https://www.wfs.nrw.de/geobasis/wfs_nw_inspire-flurstuecke_alkis",
        "typename": "cp:CadastralParcel",
        "license": "dl-de/by-2.0",
        "attribution": "© Geobasis NRW (dl-de/by-2.0)",
        "notes": "INSPIRE-konform, ALKIS-vereinfacht, Bezirksregierung Köln. Live OK 2026-05-06 (22 KB GetCapabilities)",
    },
    "BE": {  # Berlin
        "url": "https://gdi.berlin.de/services/wfs/alkis_flurstuecke",
        "typename": "cp:CadastralParcel",
        "license": "dl-de/by-2.0",
        "attribution": "© Geoportal Berlin / ALKIS Flurstücke (dl-de/by-2.0)",
        "notes": "FIS-Broker, INSPIRE-Variante. Live OK 2026-05-06 (95 KB GetCapabilities)",
    },
    "BB": {  # Brandenburg
        "url": "https://inspire.brandenburg.de/services/cp_alkis_wfs",
        "typename": "cp:CadastralParcel",
        "license": "dl-de/by-2.0",
        "attribution": "© LGB Brandenburg (dl-de/by-2.0)",
        "notes": "Frei seit 2022. Live OK 2026-05-06 (23 KB GetCapabilities)",
    },

    # ── Phase 1b — URL-Drift, HTTP 403/404/500 am 2026-05-06 ──────────
    # Die INSPIRE-Pflicht steht, aber die Endpunkt-URLs aus 2024/2025
    # sind nicht mehr gültig. Für den Live-Lookup wirken sie wie
    # Phase-2 (license-pending → query liefert None → 500m-Radius-
    # Fallback). URL-Refresh ist eigene Aufgabe (Geoportal-Recherche).
    "HH": {  # Hamburg — HTTP 404
        "url": "https://geodienste.hamburg.de/HH_WFS_INSPIRE_Cadastral_Parcels",
        "typename": "cp:CadastralParcel",
        "license": "url-broken",
        "attribution": "© Freie und Hansestadt Hamburg, LGV (dl-de/by-2.0)",
        "notes": "URL-Drift 2026-05-06 (HTTP 404). Refresh via geoportal-hamburg.de",
    },
    "SN": {  # Sachsen — HTTP 403 (möglicherweise Auth/Quota)
        "url": "https://geodienste.sachsen.de/wfs_geosn_alkis-cadastralparcels/guest",
        "typename": "cp:CadastralParcel",
        "license": "url-broken",
        "attribution": "© Staatsbetrieb Geobasisinformation und Vermessung Sachsen (GeoSN)",
        "notes": "URL-Drift 2026-05-06 (HTTP 403). Möglicherweise Auth-/Quota-Restriktion. Refresh via geoportal.sachsen.de",
    },
    "TH": {  # Thüringen — HTTP 500
        "url": "https://www.geoproxy.geoportal-th.de/geoproxy/services/INSPIRE_CP",
        "typename": "cp:CadastralParcel",
        "license": "url-broken",
        "attribution": "© TLBG Thüringen (dl-de/zero-2.0)",
        "notes": "URL-Drift 2026-05-06 (HTTP 500). Refresh via geoportal-th.de",
    },
    "MV": {  # Mecklenburg-Vorpommern — HTTP 404
        "url": "https://www.geodaten-mv.de/dienste/inspire_cp_download_wfs",
        "typename": "cp:CadastralParcel",
        "license": "url-broken",
        "attribution": "© GeoBasis-DE/MV (dl-de/by-2.0)",
        "notes": "URL-Drift 2026-05-06 (HTTP 404). Refresh via geoportal-mv.de",
    },
    "SH": {  # Schleswig-Holstein — HTTP 404
        "url": "https://service.gdi-sh.de/SH_INSPIRE_CP/wfs",
        "typename": "cp:CadastralParcel",
        "license": "url-broken",
        "attribution": "© GDI-SH (dl-de/by-2.0)",
        "notes": "URL-Drift 2026-05-06 (HTTP 404). Refresh via geoportal.schleswig-holstein.de",
    },
    "RP": {  # Rheinland-Pfalz — HTTP 403
        "url": "https://geo5.service24.rlp.de/wfs/inspire_lika",
        "typename": "cp:CadastralParcel",
        "license": "url-broken",
        "attribution": "© LVermGeo Rheinland-Pfalz (dl-de/by-2.0)",
        "notes": "URL-Drift 2026-05-06 (HTTP 403). Möglicherweise Auth nötig",
    },
    "SL": {  # Saarland — HTTP 404
        "url": "https://geoportal.saarland.de/wfs/cp/cp_alkis",
        "typename": "cp:CadastralParcel",
        "license": "url-broken",
        "attribution": "© KOMSAAR / LVGL Saarland (dl-de/by-2.0)",
        "notes": "URL-Drift 2026-05-06 (HTTP 404)",
    },
    "ST": {  # Sachsen-Anhalt — HTTP 403
        "url": "https://www.geodatenportal.sachsen-anhalt.de/wss/service/INSPIRE_LSA_CADASTRAL/guest",
        "typename": "cp:CadastralParcel",
        "license": "url-broken",
        "attribution": "© LVermGeo Sachsen-Anhalt (dl-de/by-2.0)",
        "notes": "URL-Drift 2026-05-06 (HTTP 403)",
    },
    "HB": {  # Bremen — HTTP 404
        "url": "https://geodienste.bremen.de/wfs_inspire_cp",
        "typename": "cp:CadastralParcel",
        "license": "url-broken",
        "attribution": "© Land Bremen / GeoInformation (dl-de/by-2.0)",
        "notes": "URL-Drift 2026-05-06 (HTTP 404)",
    },

    # ── Phase 2 — Lizenz-Klärung (Mails raus, Antwort steht aus) ───────
    "BY": {  # Bayern
        "url": "TBD-bayern-inspire-cp-url",
        "typename": "cp:CadastralParcel",
        "license": "pending-license",
        "attribution": "© LDBV Bayern (Lizenz in Klärung)",
        "notes": "Lizenz-Mail an inspire@ldbv.bayern.de am 2026-05-XX",
    },
    "BW": {  # Baden-Württemberg
        "url": "TBD-bw-inspire-cp-url",
        "typename": "cp:CadastralParcel",
        "license": "pending-license",
        "attribution": "© LGL Baden-Württemberg (Lizenz in Klärung)",
        "notes": "ALKIS-Volldaten kostenpflichtig, INSPIRE-Variante in Klärung",
    },
    "HE": {  # Hessen
        "url": "TBD-hessen-inspire-cp-url",
        "typename": "cp:CadastralParcel",
        "license": "pending-license",
        "attribution": "© HVBG Hessen (Lizenz in Klärung)",
        "notes": "Lizenz-Mail an geodaten@hvbg.hessen.de am 2026-05-XX",
    },
    "NI": {  # Niedersachsen
        "url": "TBD-nieders-inspire-cp-url",
        "typename": "cp:CadastralParcel",
        "license": "pending-license",
        "attribution": "© LGLN Niedersachsen (Lizenz in Klärung)",
        "notes": "Lizenz-Mail an inspire@lgln.niedersachsen.de am 2026-05-XX",
    },
}


def _bbox_around_point(lat: float, lon: float, half_deg: float = _BBOX_HALF_DEG) -> str:
    """WFS-BBox-Parameter für einen Point — ~22m-Edge.

    INSPIRE-WFS 2.0.0 mit EPSG:4326 erwartet ``minLat,minLon,maxLat,maxLon``.
    """
    return f"{lat - half_deg},{lon - half_deg},{lat + half_deg},{lon + half_deg},{_CRS}"


def _parse_inspire_response(xml_text: str, source_url: str, ep: dict[str, Any], bl: str) -> Optional[CadastralParcel]:
    """Parsing-Heuristik für INSPIRE-Cadastral-Parcels-XML.

    INSPIRE schreibt das Schema ``cp:CadastralParcel`` mit Feldern
    ``cp:nationalCadastralReference``, ``cp:areaValue``, ``cp:label``
    und einer Geometrie ``cp:geometry``. Lokale Variationen (Bayern hat
    eigenes Schema, NRW liefert ALKIS-Felder mit) werden bei Bedarf hier
    nachgepflegt.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.warning("WFS XML parse failed for %s (%s): %s", bl, source_url, e)
        return None

    # XML-Namespaces — INSPIRE-Standard
    ns = {
        "wfs": "http://www.opengis.net/wfs/2.0",
        "cp": "http://inspire.ec.europa.eu/schemas/cp/4.0",
        "gml": "http://www.opengis.net/gml/3.2",
    }

    parcel = root.find(".//cp:CadastralParcel", ns)
    if parcel is None:
        return None

    ref = parcel.findtext(".//cp:nationalCadastralReference", default=None, namespaces=ns)
    label = parcel.findtext(".//cp:label", default=None, namespaces=ns)
    area_str = parcel.findtext(".//cp:areaValue", default=None, namespaces=ns)
    try:
        area = float(area_str) if area_str else None
    except (TypeError, ValueError):
        area = None

    # Geometrie-WKT extrahieren — vereinfachter Stub. Echtes WKT-Konvert
    # aus GML braucht shapely + xmltodict, lassen wir für Phase E1.5.
    polygon_wkt = None

    # Gemarkung steckt im label oder einem extension-Feld; je nach BL
    # unterschiedlich. Stub: erstmal label durchreichen, später per-BL
    # parser-overrides.
    gemarkung = None
    flurstueck_nr = ref or label

    return CadastralParcel(
        bundesland=bl,
        gemarkung=gemarkung,
        flurstueck_nr=flurstueck_nr,
        area_m2=area,
        polygon_wkt=polygon_wkt,
        source_url=source_url,
        license=ep["license"],
        attribution=ep["attribution"],
    )


async def query_cadastral(lat: float, lon: float, bundesland: str) -> Optional[CadastralParcel]:
    """Frage das Flurstück für eine Adresse aus dem zuständigen BL-WFS.

    Returns None bei:
      - Bundesland nicht in BUNDESLAND_ENDPOINTS
      - Phase-2-Bundesland (license=pending-license)
      - Netzwerk-Fehler / Timeout
      - Kein Treffer im BBox

    Aufrufer fängt None ab und fällt auf den 500m-Radius-Pfad zurück.
    """
    bl = (bundesland or "").upper()
    ep = BUNDESLAND_ENDPOINTS.get(bl)
    if ep is None:
        logger.debug("Cadastral: bundesland %s nicht in lookup", bl)
        return None
    if ep["license"] in ("pending-license", "url-broken"):
        logger.debug(
            "Cadastral: bundesland %s nicht abrufbar (status=%s) — fallback auf 500m-Radius",
            bl, ep["license"],
        )
        return None

    url = ep["url"]
    if url.startswith("TBD"):
        logger.warning("Cadastral: URL für %s nicht gesetzt (%s)", bl, url)
        return None

    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": ep["typename"],
        "srsName": _CRS,
        "bbox": _bbox_around_point(lat, lon),
        "count": "5",  # falls Kreuzungs-Flurstück, kürzer ist besser
        "outputFormat": "application/gml+xml; version=3.2",
    }

    headers = {"User-Agent": USER_AGENT}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S, headers=headers) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return _parse_inspire_response(resp.text, url, ep, bl)
    except httpx.HTTPError as e:
        logger.warning("Cadastral WFS HTTP error for %s: %s", bl, e)
        return None
    except Exception:
        logger.exception("Cadastral WFS unexpected error for %s", bl)
        return None


def map_state_to_bundesland_code(state_name: str | None) -> str | None:
    """Mapping aus Nominatim ``region.state`` auf 2-Buchstaben-BL-Code.

    Nominatim liefert lange Namen ("Nordrhein-Westfalen"), wir brauchen
    die KFZ-Kürzel die in BUNDESLAND_ENDPOINTS als Key benutzt werden.
    """
    if not state_name:
        return None
    s = state_name.strip()
    # Vollnamen → KFZ-Codes
    mapping = {
        "Nordrhein-Westfalen": "NW",
        "Berlin": "BE",
        "Hamburg": "HH",
        "Sachsen": "SN",
        "Thüringen": "TH",
        "Brandenburg": "BB",
        "Mecklenburg-Vorpommern": "MV",
        "Schleswig-Holstein": "SH",
        "Rheinland-Pfalz": "RP",
        "Saarland": "SL",
        "Sachsen-Anhalt": "ST",
        "Bremen": "HB",
        "Bayern": "BY",
        "Baden-Württemberg": "BW",
        "Hessen": "HE",
        "Niedersachsen": "NI",
    }
    return mapping.get(s)
