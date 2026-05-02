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
        "short": "SOC, pH, Schwermetalle, Textur nach EU-Bodenmonitoring-Richtlinie",
        "description": (
            "Alle 13 Bodendescriptoren der EU-Bodenmonitoring-Richtlinie 2025/2360 "
            "(Anhang I, Teile A bis C) plus 4 Versiegelungs-Indikatoren in Teil D. "
            "Compliance-Basis ab nationaler Umsetzung bis Dezember 2028."
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

    # ── 5 Bonus-Indikatoren über die EU-Pflicht hinaus ─────────────────
    # Mappen 1:1 auf die Items in soil_directive.py "bonus_indicators".
    # Buchbar als optionale Zusatzmodule. Werden im Vollbericht in einer
    # separaten Sektion "Über die EU-Pflicht hinaus" gezeigt — nur die
    # gebuchten Module sind dort befüllt, die anderen ausgegraut.
    {
        "key": "bonus-wind-erosion",
        "name": "Wind-Erosion separat (RWEQ)",
        "short": "Eigenständige Wind-Erosions-Bewertung neben RUSLE",
        "description": (
            "Über EU-Anhang I hinaus: Wind-Erosion separat ausgewiesen "
            "(in der Richtlinie nur als Teil der Gesamt-Erosionsrate). "
            "RWEQ-Approximation aus Sand-Anteil, Lat, Hangneigung. "
            "Relevant für Norddeutschland, Veluwe und Drenthe."
        ),
        "sources": ["SoilGrids 250m", "SRTM Hangneigung"],
        "price_eur": 5.00,
        "included_in_base": False,
        "category": "bonus",
    },
    {
        "key": "bonus-pak-pcb",
        "name": "PAK/PCB Altlast-Screening",
        "short": "BBodSchV-relevante organische Schadstoffe — Vornutzungs-Verdacht",
        "description": (
            "Über EU-Anhang I hinaus: PAK (Σ16) und PCB nach BBodSchV §8 "
            "Anhang 1. Wird bei Vornutzungs-Verdacht (Schmiede, Tankstelle, "
            "Trafostation, Schießstand) als Standard-Untersuchungspaket geführt. "
            "Kennzeichnet relevante Verdachtsflächen als not_remote für "
            "anschließende In-situ-Beprobung."
        ),
        "sources": ["BBodSchV Anhang 1", "Vornutzungs-Indikatoren aus CORINE/OSM"],
        "price_eur": 15.00,
        "included_in_base": False,
        "category": "bonus",
    },
    {
        "key": "bonus-microbial-activity",
        "name": "Mikrobielle Aktivität",
        "short": "Boden-Atmungsrate und mikrobielle Biomasse als Vitalitäts-Indikator",
        "description": (
            "Über EU-Anhang I hinaus: Boden-Atmungsrate und mikrobielle "
            "Biomasse zusätzlich zur DNA-Biodiversität (EU-Pflicht-Teil C). "
            "Wo LUCAS-Soil-Biology-Daten verfügbar sind, ergänzen wir die "
            "Approximation; sonst not_remote."
        ),
        "sources": ["LUCAS Soil Biology", "In-situ-Inkubation"],
        "price_eur": 8.00,
        "included_in_base": False,
        "category": "bonus",
    },
    {
        "key": "bonus-soil-structure",
        "name": "Bodenstruktur und Aggregat-Stabilität",
        "short": "Erosions- und Versickerungs-Vorlauf aus Korngröße und SOC",
        "description": (
            "Über EU-Anhang I hinaus: Aggregat-Stabilitäts-Index aus Ton-Anteil "
            "und SOC-Konzentration. Voller Test in DIN ISO 10930 (Nasssiebung) "
            "bleibt Goldstandard, unsere Approximation ist Vorab-Indikator."
        ),
        "sources": ["SoilGrids 250m (clay, soc)"],
        "price_eur": 5.00,
        "included_in_base": False,
        "category": "bonus",
    },
    {
        "key": "bonus-hydromorphology",
        "name": "Hydromorphologie und Drainage",
        "short": "Wasserhaltungs-Eigenschaften aus WRB-Bodenklasse + Hangneigung",
        "description": (
            "Über EU-Anhang I hinaus: Hydromorphologie- und Drainage-Klasse "
            "aus WRB-Soil-Klassifikation und Hangneigung. Relevant für "
            "Hochwasser-Vorlauf, Versickerungs- und Wurzeltiefe-Analysen."
        ),
        "sources": ["SoilGrids WRB", "SRTM Hangneigung"],
        "price_eur": 8.00,
        "included_in_base": False,
        "category": "bonus",
    },
]


@router.get("/modules")
async def list_modules() -> dict:
    return {
        "base_price_eur": BASE_PRICE_EUR,
        "currency": "EUR",
        "modules": MODULES_CATALOG,
    }
