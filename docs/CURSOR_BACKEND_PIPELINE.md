# Backend Pipeline: Mock → Real Data

## Ziel

Alle Mock-Funktionen in `backend/app/routers/reports.py` durch echte Datenquellen ersetzen.
Das Frontend und die API-Schemas bleiben **unverändert** — nur die Daten werden echt.

---

## Schritt 1: Geocoding — `_mock_geocode()` ersetzen

**Datei:** `backend/app/routers/reports.py` Zeile 28-34

**Aktuell:** SHA256-Hash → fake Koordinaten.

**Ersetzen durch:** Nominatim (OpenStreetMap) Geocoding.

```python
import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

async def geocode_address(address: str) -> tuple[float, float, str]:
    """Returns (lat, lon, display_name). Raises HTTPException on failure."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            NOMINATIM_URL,
            params={
                "q": address,
                "format": "json",
                "limit": 1,
                "countrycodes": "de,nl,at,ch",
            },
            headers={"User-Agent": "GeoForensic/1.0 (kontakt@geoforensic.de)"},
            timeout=10.0,
        )
        resp.raise_for_status()
        results = resp.json()

    if not results:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Adresse konnte nicht gefunden werden",
        )

    hit = results[0]
    return float(hit["lat"]), float(hit["lon"]), hit["display_name"]
```

**Wichtig:**
- `httpx` zu `requirements.txt` hinzufügen
- Nominatim Usage Policy: max 1 Request/Sekunde, User-Agent Pflicht
- `PreviewResponse.address_resolved` mit `display_name` befüllen statt `payload.address.strip()`
- Für Preview UND Create die gleiche Funktion nutzen

---

## Schritt 2: EGMS-Daten laden und abfragen

### 2a: Datenbeschaffung

EGMS Ortho L3 Daten herunterladen von https://egms.land.copernicus.eu/

- Format: CSV oder GeoPackage
- Produkt: **L3 Ortho — Vertical Component**
- Auflösung: 100m Grid
- Felder pro Punkt: `latitude, longitude, mean_velocity_mm_yr, velocity_std, coherence, measurement_period_start, measurement_period_end`
- Zeitreihen: jeder Punkt hat eine Displacement-Zeitreihe (Datum → kumulative Verschiebung in mm)

Die Dateien sind groß (mehrere GB pro Land). Für den Start:
1. Deutschland komplett herunterladen
2. Niederlande komplett herunterladen
3. In PostGIS laden (siehe 2b)

### 2b: PostGIS-Import

Neue Tabelle in der bestehenden PostgreSQL-DB:

```sql
-- PostGIS Extension aktivieren
CREATE EXTENSION IF NOT EXISTS postgis;

-- Haupttabelle für EGMS-Messpunkte
CREATE TABLE egms_points (
    id BIGSERIAL PRIMARY KEY,
    geom GEOMETRY(Point, 4326) NOT NULL,
    mean_velocity_mm_yr REAL NOT NULL,
    velocity_std REAL,
    coherence REAL,
    measurement_start DATE,
    measurement_end DATE,
    country CHAR(2) NOT NULL DEFAULT 'DE'
);

-- Räumlicher Index — KRITISCH für Performance
CREATE INDEX idx_egms_points_geom ON egms_points USING GIST (geom);

-- Zeitreihen (optional, für Premium-Report)
CREATE TABLE egms_timeseries (
    point_id BIGINT REFERENCES egms_points(id),
    measurement_date DATE NOT NULL,
    displacement_mm REAL NOT NULL,
    PRIMARY KEY (point_id, measurement_date)
);
```

**Import-Script** (Python, einmalig):

```python
"""import_egms.py — EGMS CSV nach PostGIS laden."""
import csv
from pathlib import Path
from sqlalchemy import text
from app.database import engine  # sync engine für Bulk-Import

def import_egms_csv(csv_path: Path, country: str = "DE"):
    with engine.begin() as conn, open(csv_path) as f:
        reader = csv.DictReader(f)
        batch = []
        for i, row in enumerate(reader):
            batch.append({
                "lat": float(row["latitude"]),
                "lon": float(row["longitude"]),
                "vel": float(row["mean_velocity"]),
                "std": float(row.get("velocity_std", 0)),
                "coh": float(row.get("coherence", 0)),
                "country": country,
            })
            if len(batch) >= 10000:
                conn.execute(text("""
                    INSERT INTO egms_points (geom, mean_velocity_mm_yr, velocity_std, coherence, country)
                    VALUES (ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :vel, :std, :coh, :country)
                """), batch)
                batch = []
                print(f"  {i+1} Punkte importiert...")
        if batch:
            conn.execute(text("...gleiche Query..."), batch)
    print(f"Import fertig: {csv_path}")
```

**requirements.txt ergänzen:** `geoalchemy2` (für PostGIS-Support in SQLAlchemy)

### 2c: Radius-Query Funktion

```python
from sqlalchemy import text

async def query_egms_points(
    db: AsyncSession,
    lat: float,
    lon: float,
    radius_m: int = 500,
) -> list[dict]:
    """Alle EGMS-Punkte im Umkreis von radius_m Metern."""
    result = await db.execute(
        text("""
            SELECT
                ST_Y(geom) as lat,
                ST_X(geom) as lon,
                mean_velocity_mm_yr,
                velocity_std,
                coherence,
                ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) as distance_m
            FROM egms_points
            WHERE ST_DWithin(
                geom::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius
            )
            ORDER BY distance_m
        """),
        {"lat": lat, "lon": lon, "radius": radius_m},
    )
    return [dict(row._mapping) for row in result]
```

---

## Schritt 3: Echte Analyse-Pipeline — `_run_mock_report_pipeline()` ersetzen

**Datei:** `backend/app/routers/reports.py` Zeile 45-80

Komplette Funktion ersetzen:

```python
async def _run_report_pipeline(report_id: uuid.UUID) -> None:
    async with SessionLocal() as db:
        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if report is None:
            return

        try:
            # 1. EGMS-Punkte im Radius abfragen
            points = await query_egms_points(db, report.latitude, report.longitude, report.radius_m)

            if not points:
                report.status = ReportStatus.completed
                report.ampel = Ampel.gruen
                report.geo_score = 95
                report.report_data = {
                    "analysis": {
                        "summary": "Keine EGMS-Messpunkte im Untersuchungsradius gefunden.",
                        "point_count": 0,
                        "max_abs_velocity_mm_yr": 0.0,
                        "mean_velocity_mm_yr": 0.0,
                        "median_velocity_mm_yr": 0.0,
                    },
                    "raw_points": [],
                }
                await db.commit()
                return

            # 2. Statistiken berechnen
            velocities = [abs(p["mean_velocity_mm_yr"]) for p in points]
            max_vel = max(velocities)
            mean_vel = sum(velocities) / len(velocities)
            sorted_vel = sorted(velocities)
            median_vel = sorted_vel[len(sorted_vel) // 2]

            # Gewichteter Score: nächste Punkte zählen mehr
            # (distance_m ist in den points enthalten)
            weighted_vel = sum(
                abs(p["mean_velocity_mm_yr"]) * max(0.1, 1.0 - p["distance_m"] / report.radius_m)
                for p in points
            ) / sum(
                max(0.1, 1.0 - p["distance_m"] / report.radius_m)
                for p in points
            )

            # 3. Ampel + Score
            ampel, geo_score = _ampel_from_velocity(weighted_vel)

            # 4. report_data zusammenbauen
            report.ampel = ampel
            report.geo_score = geo_score
            report.status = ReportStatus.completed
            report.report_data = {
                "analysis": {
                    "summary": f"Analyse basierend auf {len(points)} EGMS-Messpunkten "
                               f"im Radius von {report.radius_m}m.",
                    "point_count": len(points),
                    "max_abs_velocity_mm_yr": round(max_vel, 2),
                    "mean_velocity_mm_yr": round(mean_vel, 2),
                    "median_velocity_mm_yr": round(median_vel, 2),
                    "weighted_velocity_mm_yr": round(weighted_vel, 2),
                    "data_source": "EGMS Ortho L3 (Copernicus)",
                    "attribution": "Generated using European Union's Copernicus Land Monitoring Service information",
                },
                "velocity_histogram": _build_histogram(velocities),
                "geo_score": geo_score,
                "raw_points": [
                    {
                        "lat": round(p["lat"], 6),
                        "lon": round(p["lon"], 6),
                        "velocity_mm_yr": round(p["mean_velocity_mm_yr"], 2),
                        "distance_m": round(p["distance_m"], 1),
                        "coherence": round(p.get("coherence", 0), 2),
                    }
                    for p in points[:200]  # Max 200 Punkte im Response
                ],
            }
            await db.commit()

        except Exception as e:
            report.status = ReportStatus.failed
            report.report_data = {"error": str(e)}
            await db.commit()


def _build_histogram(velocities: list[float]) -> dict:
    """Velocity-Verteilung in Bins für Frontend-Chart."""
    bins = {"0-2": 0, "2-5": 0, "5-8": 0, "8-12": 0, "12+": 0}
    for v in velocities:
        if v < 2: bins["0-2"] += 1
        elif v < 5: bins["2-5"] += 1
        elif v < 8: bins["5-8"] += 1
        elif v < 12: bins["8-12"] += 1
        else: bins["12+"] += 1
    return bins
```

**Aufruf in `create_report` anpassen** (Zeile 121):
```python
# ALT:
background_tasks.add_task(_run_mock_report_pipeline, report.id)
# NEU:
background_tasks.add_task(_run_report_pipeline, report.id)
```

---

## Schritt 4: Preview-Endpoint mit echten Daten

**Datei:** `backend/app/routers/reports.py` Zeile 83-97

```python
@router.post("/preview", response_model=PreviewResponse)
@limiter.limit("10/hour")
async def preview_report(
    request: Request,
    payload: PreviewRequest,
    db: AsyncSession = Depends(get_db),
) -> PreviewResponse:
    lat, lon, display_name = await geocode_address(payload.address)

    # Schnelle Punkt-Zählung + Max-Velocity im Default-Radius (500m)
    points = await query_egms_points(db, lat, lon, radius_m=500)
    if points:
        max_vel = max(abs(p["mean_velocity_mm_yr"]) for p in points)
        ampel, _ = _ampel_from_velocity(max_vel)
    else:
        ampel = Ampel.gruen
        max_vel = 0.0

    return PreviewResponse(
        ampel=ampel.value,
        point_count=len(points),
        address_resolved=display_name,
        latitude=lat,
        longitude=lon,
    )
```

**ACHTUNG:** Preview braucht jetzt `db` Dependency — zum Imports hinzufügen.

---

## Schritt 5: Echte PDF-Generierung

**Datei:** `backend/app/routers/reports.py` Zeile 157-174

**Dependency hinzufügen:** `weasyprint` in `requirements.txt`

Neue Datei: `backend/app/pdf_generator.py`

```python
"""PDF-Report-Generierung mit WeasyPrint."""
from pathlib import Path
from weasyprint import HTML

TEMPLATE_DIR = Path(__file__).parent / "templates"

def generate_report_pdf(report) -> bytes:
    """Generiert PDF aus report_data. Returns bytes."""
    data = report.report_data or {}
    analysis = data.get("analysis", {})
    points = data.get("raw_points", [])

    # HTML-Template rendern
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{ size: A4; margin: 2cm; }}
            body {{
                font-family: 'Helvetica Neue', Arial, sans-serif;
                color: #1a1a1a;
                font-size: 11pt;
                line-height: 1.5;
            }}
            .header {{
                border-bottom: 3px solid #22C55E;
                padding-bottom: 16px;
                margin-bottom: 24px;
            }}
            .header h1 {{
                font-size: 24pt;
                margin: 0;
                letter-spacing: 2px;
                text-transform: uppercase;
            }}
            .header .subtitle {{
                color: #666;
                font-size: 10pt;
                margin-top: 4px;
            }}
            .ampel {{
                display: inline-block;
                padding: 8px 24px;
                border-radius: 4px;
                font-size: 14pt;
                font-weight: bold;
                color: white;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .ampel-gruen {{ background: #22C55E; }}
            .ampel-gelb {{ background: #EAB308; color: #1a1a1a; }}
            .ampel-rot {{ background: #EF4444; }}
            .kpi-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 12px;
                margin: 20px 0;
            }}
            .kpi {{
                border: 1px solid #ddd;
                padding: 12px;
                text-align: center;
            }}
            .kpi .value {{
                font-size: 18pt;
                font-weight: bold;
            }}
            .kpi .label {{
                font-size: 8pt;
                color: #666;
                text-transform: uppercase;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 9pt;
                margin-top: 16px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 6px 8px;
                text-align: right;
            }}
            th {{
                background: #f5f5f5;
                text-align: center;
            }}
            .disclaimer {{
                margin-top: 32px;
                padding-top: 16px;
                border-top: 1px solid #ddd;
                font-size: 7pt;
                color: #999;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>GeoForensic</h1>
            <div class="subtitle">Bodenbewegungsscreening &mdash; Standortauskunft</div>
        </div>

        <p><strong>Adresse:</strong> {report.address_input}</p>
        <p><strong>Koordinaten:</strong> {report.latitude:.6f}, {report.longitude:.6f}</p>
        <p><strong>Untersuchungsradius:</strong> {report.radius_m} m</p>
        <p><strong>Erstellt:</strong> {report.created_at.strftime('%d.%m.%Y %H:%M')} UTC</p>
        {f'<p><strong>Aktenzeichen:</strong> {report.aktenzeichen}</p>' if report.aktenzeichen else ''}

        <h2>Ergebnis</h2>
        <span class="ampel ampel-{report.ampel.value if report.ampel else 'gruen'}">
            {report.ampel.value.upper() if report.ampel else 'GRÜN'}
        </span>

        <div class="kpi-grid">
            <div class="kpi">
                <div class="value">{analysis.get('point_count', 0)}</div>
                <div class="label">Messpunkte</div>
            </div>
            <div class="kpi">
                <div class="value">{analysis.get('max_abs_velocity_mm_yr', 0):.1f}</div>
                <div class="label">Max. Geschwindigkeit (mm/a)</div>
            </div>
            <div class="kpi">
                <div class="value">{report.geo_score or 0}</div>
                <div class="label">GeoScore</div>
            </div>
        </div>

        <h3>Zusammenfassung</h3>
        <p>{analysis.get('summary', '')}</p>

        <h3>Messpunkte ({min(len(points), 30)} von {analysis.get('point_count', 0)})</h3>
        <table>
            <tr>
                <th>Nr.</th>
                <th>Breitengrad</th>
                <th>Längengrad</th>
                <th>Geschwindigkeit (mm/a)</th>
                <th>Entfernung (m)</th>
            </tr>
            {''.join(f"""
            <tr>
                <td>{i+1}</td>
                <td>{p.get('lat', 0):.6f}</td>
                <td>{p.get('lon', 0):.6f}</td>
                <td>{p.get('velocity_mm_yr', 0):.2f}</td>
                <td>{p.get('distance_m', 0):.0f}</td>
            </tr>""" for i, p in enumerate(points[:30]))}
        </table>

        <div class="disclaimer">
            <p><strong>Hinweis:</strong> Diese Standortauskunft ist ein automatisiertes
            Datenscreening auf Basis von Satellitenfernerkundungsdaten (InSAR). Sie ersetzt
            keine Ortsbesichtigung, kein Baugrundgutachten und keine fachliche Beratung
            durch einen Sachverständigen. Die Daten stammen aus dem European Ground Motion
            Service (EGMS) des Copernicus-Programms der EU. Für die Richtigkeit und
            Vollständigkeit der Quelldaten wird keine Gewährleistung übernommen.</p>
            <p>Generated using European Union's Copernicus Land Monitoring Service information.</p>
            <p>&copy; GeoForensic {report.created_at.year} &mdash; Alle Rechte vorbehalten.</p>
        </div>
    </body>
    </html>
    """

    return HTML(string=html_content).write_pdf()
```

**PDF-Endpoint in reports.py anpassen:**

```python
from app.pdf_generator import generate_report_pdf

@router.get("/{report_id}/pdf")
async def get_report_pdf(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    report = await _get_report_for_user(report_id, current_user.id, db)
    if not report.paid:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Report is not paid")

    pdf_bytes = generate_report_pdf(report)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="geoforensic-{report.id}.pdf"'},
    )
```

---

## Schritt 6: requirements.txt aktualisieren

```
fastapi
uvicorn[standard]
sqlalchemy[asyncio]
asyncpg
alembic
pydantic-settings
python-jose[cryptography]
passlib[bcrypt]
stripe
slowapi
email-validator
httpx
geoalchemy2
weasyprint
```

---

## Schritt 7: Alembic-Migration für PostGIS

```bash
alembic revision --autogenerate -m "add egms_points table"
```

Falls Alembic PostGIS nicht automatisch erkennt, manuell eine Migration erstellen:

```python
"""add egms_points table"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("""
        CREATE TABLE egms_points (
            id BIGSERIAL PRIMARY KEY,
            geom GEOMETRY(Point, 4326) NOT NULL,
            mean_velocity_mm_yr REAL NOT NULL,
            velocity_std REAL,
            coherence REAL,
            measurement_start DATE,
            measurement_end DATE,
            country CHAR(2) NOT NULL DEFAULT 'DE'
        )
    """)
    op.execute("CREATE INDEX idx_egms_points_geom ON egms_points USING GIST (geom)")

def downgrade():
    op.execute("DROP TABLE IF EXISTS egms_points")
```

---

## Reihenfolge der Umsetzung

1. **`httpx` installieren, `geocode_address()` schreiben, Preview-Endpoint umstellen** → sofort testbar
2. **PostGIS Extension + `egms_points` Tabelle anlegen** → Migration
3. **EGMS-Daten herunterladen + Import-Script ausführen** → einmalig
4. **`query_egms_points()` schreiben + `_run_report_pipeline()` ersetzen** → Create-Endpoint umstellen
5. **`weasyprint` installieren + `pdf_generator.py` anlegen + PDF-Endpoint umstellen**
6. **Testen:** Preview → Create → PDF Download

---

## Was NICHT geändert werden soll

- Frontend bleibt komplett wie es ist
- API-Response-Schemas bleiben gleich (PreviewResponse, ReportDetailResponse, etc.)
- Auth-Flow bleibt gleich
- Stripe-Integration bleibt gleich
- `_ampel_from_velocity()` bleibt gleich
- Database Models (Report, User, Payment) bleiben gleich — nur `report_data` JSONB bekommt echte Daten statt Mock

## EGMS-Daten Download

1. Geh auf https://egms.land.copernicus.eu/
2. Wähle "Download" → "Ortho" → "L3" → "Vertical"
3. Deutschland: alle Tiles die DE abdecken
4. Format: CSV bevorzugt (einfacher zu importieren als GeoPackage)
5. Die Dateien sind mehrere GB groß — Geduld beim Download

## Attribution (rechtlich erforderlich)

Jeder Report MUSS enthalten:
> "Generated using European Union's Copernicus Land Monitoring Service information"

Dies ist bereits im PDF-Template und in `report_data.analysis.attribution` eingebaut.
