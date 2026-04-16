"""Module catalog endpoint — lists available report modules with prices."""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["modules"])

BASE_PRICE_EUR = 49.00

MODULES_CATALOG = [
    {
        "key": "insar-bodenbewegung",
        "name": "InSAR Bodenbewegung",
        "short": "Vertikale Bodenbewegung via Satellit (Sentinel-1, 100m-Raster)",
        "description": (
            "Millimeter-genaue Auswertung der Bodenbewegung über 5 Jahre. "
            "Zeitreihe, Trend, R², Kartendarstellung und Ampel-Bewertung."
        ),
        "sources": ["Copernicus EGMS L3 Ortho", "BGR Bodenbewegungsdienst"],
        "price_eur": 0.0,
        "included_in_base": True,
        "category": "geophysik",
    },
    {
        "key": "hochwasser-ror",
        "name": "Hochwasser-Risikozonen",
        "short": "EU-Hochwasserrichtlinie 2007/60/EG — HQ100 / HQextrem",
        "description": (
            "Zuordnung der Adresse zu offiziellen Risikozonen nach "
            "EU-Hochwasserrichtlinie. Fluvial + pluvial."
        ),
        "sources": ["PDOK ROR (NL)", "LUBW/LANUV (DE)", "Copernicus EMS Events"],
        "price_eur": 12.00,
        "included_in_base": False,
        "category": "hazard",
    },
    {
        "key": "klimaatlas",
        "name": "Klimaadaptations-Profil",
        "short": "Hitze, Starkregen, Dürre-Projektion 5J + 30J",
        "description": (
            "Regionalisierte Klimaprojektionen aus den offiziellen "
            "Klimaadaptations-Atlanten. Drei Szenarien (moderat/mittel/hoch)."
        ),
        "sources": ["Klimaateffectatlas NL", "UBA KliVO DE"],
        "price_eur": 14.00,
        "included_in_base": False,
        "category": "hazard",
    },
    {
        "key": "altlasten",
        "name": "Altlasten-Screening",
        "short": "Historische Bodenbelastung + bekannte Altstandorte",
        "description": (
            "Abfrage kantonal/bundeslandbezogener Altlastenregister. "
            "Meldungen inklusive Koordinaten-Distanz."
        ),
        "sources": ["Bodemloket NL", "LUBW Altlastenkataster BW", "LANUV NRW Altlasten"],
        "price_eur": 18.00,
        "included_in_base": False,
        "category": "kontamination",
    },
    {
        "key": "funderingslabel",
        "name": "Funderingslabel-Faktoren (NL)",
        "short": "Bodentyp, Grundwasser, Bauart — Basis A-E Label",
        "description": (
            "Die 5 Faktoren hinter dem seit 1.4.2026 verpflichtenden NL "
            "Funderingslabel. Liefert die technische Basis für den "
            "NRVT-Taxateur."
        ),
        "sources": ["PDOK Bodemkaart", "DINOloket TNO Grundwasser", "BAG"],
        "price_eur": 24.00,
        "included_in_base": False,
        "category": "fundament",
        "regions": ["NL"],
    },
    {
        "key": "bergbau",
        "name": "Bergbau-Altlasten (DE)",
        "short": "Steinkohle/Braunkohle/Kali — bekannte Senkungsgebiete",
        "description": (
            "Deutsche Bergbau-Risiko-Zuordnung. Aktive + stillgelegte "
            "Reviere, Senkungsgebiete, Grubenhohlräume."
        ),
        "sources": ["BGR GUEK200", "Landesbergämter"],
        "price_eur": 16.00,
        "included_in_base": False,
        "category": "hazard",
        "regions": ["DE"],
    },
    {
        "key": "radon",
        "name": "Radon-Vorsorgegebiet",
        "short": "Zuordnung zu amtlichen Vorsorgegebieten (§121 StrlSchG)",
        "description": (
            "Prüfung ob Adresse in einem Radon-Vorsorgegebiet gemäß "
            "§121 Strahlenschutzgesetz liegt. Inkl. Bq/m³-Schätzung."
        ),
        "sources": ["BfS Radon-Karte", "Kantonale Radon-Register"],
        "price_eur": 9.00,
        "included_in_base": False,
        "category": "hazard",
        "regions": ["DE", "CH", "AT"],
    },
    {
        "key": "bodenqualitaet",
        "name": "Bodenqualität (EU 2025/2360)",
        "short": "SOC, pH, Schwermetalle, Textur nach EU-Bodendirektive",
        "description": (
            "Die 12 bodenchemischen Kennwerte aus EU-Bodenmonitoring-"
            "Direktive 2025/2360. Compliance-Basis ab Mitte 2027 Pflicht."
        ),
        "sources": ["SoilGrids 250m", "LUCAS 2022 Topsoil"],
        "price_eur": 22.00,
        "included_in_base": False,
        "category": "umwelt",
    },
    {
        "key": "gebaeudedaten",
        "name": "Gebäude-Detaildaten (BAG/ALKIS)",
        "short": "Baujahr, Nutzfunktion, Pand-Polygon, Oberfläche",
        "description": (
            "Objektbezogene Gebäudedaten aus amtlichen Registern "
            "(BAG-NL / ALKIS-DE). Pro Gebäude im Umkreis von 50 m."
        ),
        "sources": ["BAG NL (PDOK WFS)", "ALKIS/AAA (Landesvermessung)"],
        "price_eur": 8.00,
        "included_in_base": False,
        "category": "kontext",
    },
]


@router.get("/modules")
async def list_modules() -> dict:
    return {
        "base_price_eur": BASE_PRICE_EUR,
        "currency": "EUR",
        "modules": MODULES_CATALOG,
    }
