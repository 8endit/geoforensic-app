"""Provenance-Page Route — Empfaenger des QR-Codes auf dem Vollbericht-Cover.

Vollbericht-Cover hat einen QR-Code der auf bodenbericht.de/r/{report_id}
zeigt. Dort findet der Leser:
- Bestaetigung dass dieser Bericht in unserer DB existiert
- Generierungs-Datum
- Liste der Datenquellen (EGMS / SoilGrids / LUCAS / KOSTRA / BfG / etc.)
- Cryptographischer Hash zur Verifikation gegen Manipulation

Bewusst KEINE Adresse + keine Werte gezeigt — der Empfaenger der Mail
hat das PDF, andere QR-Scanner kennen die Adresse nicht. Datenschutz.

Page ist HTML (kein API), unterhalb /r/* gemountet (nicht /api/*) damit
QR-Reader sauber rein navigieren.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Report

logger = logging.getLogger(__name__)

router = APIRouter(tags=["provenance"])

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATES = _BACKEND_ROOT / "templates" / "provenance"


def _provenance_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )


def _report_fingerprint(r: Report) -> str:
    """Stabile SHA-256-Verkuerzung als Manipulations-Indikator.

    Nimmt nur Felder die sich nach Versand nicht aendern duerfen — der
    Empfaenger kann sein PDF vor sich haben und am Hash erkennen ob die
    Server-Variante davon abweicht (Phase 2: Hash-In-PDF einbetten +
    Vergleich automatisieren). Aktuell nur als 'hier-existiert-Bericht'-
    Token sichtbar.
    """
    parts = [
        str(r.id),
        f"{r.latitude:.5f}",
        f"{r.longitude:.5f}",
        r.ampel.value if r.ampel else "none",
        str(r.geo_score or ""),
        r.created_at.isoformat() if r.created_at else "",
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16].upper()


@router.get("/r/{report_id}", response_class=HTMLResponse)
async def provenance_page(report_id: str) -> HTMLResponse:
    """Public provenance lookup. Gibt 404 wenn report_id unbekannt.

    Antwort ist HTML — bewusst keine Adresse / Messwerte sichtbar (nur
    der Empfaenger der Mail hat das PDF). Zeigt nur:
    - Datum
    - Datenquellen-Liste
    - Hash zur Manipulations-Pruefung
    """
    try:
        rid = uuid.UUID(report_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    async with SessionLocal() as db:
        result = await db.execute(select(Report).where(Report.id == rid))
        report = result.scalar_one_or_none()

    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Datenquellen-Liste: aus dem report_data JSONB rauszieh, fallback
    # auf einen statischen Default (Bericht aus VOR-Persistenz-Aera).
    sources_default = [
        ("EGMS", "European Ground Motion Service · Copernicus", "CC BY 4.0"),
        ("SoilGrids 250m", "ISRIC World Soil Information", "CC BY 4.0"),
        ("LUCAS Topsoil", "JRC ESDAC", "EU Open Data"),
        ("KOSTRA-DWD-2020", "Deutscher Wetterdienst", "GeoNutzV"),
        ("HWRM-RL", "Bundesanstalt fuer Gewaesserkunde", "DL-DE/Zero-2.0"),
        ("CORINE 2018", "Copernicus Land Monitoring Service", "Copernicus FFO"),
        ("OpenStreetMap", "OSM Contributors", "ODbL"),
    ]

    fingerprint = _report_fingerprint(report)
    env = _provenance_env()
    html = env.get_template("report.html").render(
        report_id=str(report.id),
        created_at=report.created_at.strftime("%d.%m.%Y · %H:%M Uhr") if report.created_at else "—",
        country=(report.country or "DE").upper(),
        fingerprint=fingerprint,
        sources=sources_default,
        now=datetime.utcnow().strftime("%d.%m.%Y"),
    )
    return HTMLResponse(content=html, status_code=200)
