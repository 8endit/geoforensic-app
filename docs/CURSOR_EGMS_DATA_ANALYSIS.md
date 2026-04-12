# Aufgabe: EGMS-Daten herunterladen, analysieren und Import-Script bauen

## Kontext

Die Backend-Pipeline ist fertig (`reports.py` queried `egms_points` via PostGIS).
Die Tabelle existiert (`egms_points` + `egms_timeseries`).
Aber: **Die Tabelle ist leer.** Ohne Daten liefert jeder Report "0 Messpunkte, grün".

Diese Aufgabe hat zwei Teile:
1. EGMS-Daten herunterladen und analysieren (Machbarkeitscheck)
2. Import-Script bauen das die Daten in PostGIS lädt

---

## Teil 1: Datensatz herunterladen und analysieren

### 1a: Download

Geh auf https://egms.land.copernicus.eu/ → "Download" Bereich.

Lade den **EGMS Ortho L3** Datensatz herunter:
- **Produkt:** L3 Ortho (vertikale Komponente)
- **Format:** CSV bevorzugt (einfacher zu parsen als GeoPackage)
- **Regionen:** 
  - Eine Tile/Region die **Rotterdam/Gouda** (Niederlande) abdeckt
  - Eine Tile/Region die das **Ruhrgebiet** (Deutschland) abdeckt
- Falls die Download-Seite nur GeoPackage/GeoTIFF anbietet, ist das auch OK

**ACHTUNG:** Die Dateien können mehrere GB groß sein. Notiere die exakte Dateigröße.

### 1b: Datensatz-Analyse

Nachdem der Download fertig ist, beantworte diese Fragen mit echten Zahlen:

**Struktur:**
- [ ] Welches Format hat die Datei? (CSV, GeoPackage, GeoTIFF, anderes?)
- [ ] Welche Spalten/Felder hat der Datensatz? (Exakte Spaltennamen + Datentypen)
- [ ] Wie heißen die Koordinaten-Felder? (lat/lon, easting/northing, WKT?)
- [ ] Welches Koordinatensystem? (WGS84/EPSG:4326, UTM, anderes?)
- [ ] Gibt es ein Feld für `mean_velocity` (mm/Jahr)? Wie heißt es genau?
- [ ] Gibt es `velocity_std` und `coherence` Felder?
- [ ] Gibt es Zeitreihen-Daten (displacement pro Datum) oder nur Durchschnittswerte?

**Dichte:**
- [ ] Wie viele Punkte enthält der Datensatz insgesamt?
- [ ] Wie viele Punkte pro km² in einer typischen **Stadt** (Rotterdam Centrum)?
- [ ] Wie viele Punkte pro km² in einem typischen **Vorort**?
- [ ] Wie viele Punkte pro km² auf dem **Land**?
- [ ] Wie viele Punkte fallen in einen **500m-Radius** um eine typische Stadtadresse?
- [ ] Wie viele Punkte fallen in einen **500m-Radius** auf dem Land?

**Qualität:**
- [ ] Velocity-Range: Was ist min/max/mean/median mm/Jahr im Datensatz?
- [ ] Gibt es offensichtliche Ausreißer?
- [ ] Was ist der Coherence-Range? (0-1, wobei > 0.6 typisch "gut" ist)
- [ ] Gibt es Lücken/NULL-Werte?

**Reicht die Auflösung für einen Adress-Report?**
Das ist die Kernfrage. Wenn in einem 500m-Radius um ein Stadthaus nur 2-3 Punkte liegen,
ist der Report statistisch wertlos. Wenn 50+ Punkte da sind, ist er solide.

Schreibe die Ergebnisse in `docs/EGMS_DATA_REPORT.md`.

---

## Teil 2: Import-Script

Erst NACH Teil 1 — nur wenn die Daten brauchbar sind.

### 2a: Script erstellen

Neue Datei: `backend/scripts/import_egms.py`

Das Script muss:
1. Eine EGMS-Datendatei lesen (CSV oder GeoPackage, je nach Download-Format)
2. Koordinaten nach EPSG:4326 (WGS84) konvertieren falls nötig
3. Batch-Insert in die `egms_points` Tabelle (10.000er Batches für Performance)
4. Fortschritt loggen (alle 50.000 Punkte)
5. Duplikate ignorieren (ON CONFLICT DO NOTHING oder Prüfung)
6. Am Ende: Anzahl importierter Punkte ausgeben

```python
"""Import EGMS data into PostGIS.

Usage:
    python -m scripts.import_egms path/to/egms_data.csv --country DE
    python -m scripts.import_egms path/to/egms_data.gpkg --country NL
"""
```

### 2b: Mapping zur DB-Tabelle

Die `egms_points` Tabelle hat diese Spalten:

```sql
id BIGSERIAL PRIMARY KEY,
geom GEOMETRY(Point, 4326) NOT NULL,       -- ST_SetSRID(ST_MakePoint(lon, lat), 4326)
mean_velocity_mm_yr REAL NOT NULL,
velocity_std REAL,
coherence REAL,
measurement_start DATE,
measurement_end DATE,
country CHAR(2) NOT NULL DEFAULT 'DE'
```

Das Script muss die EGMS-Felder auf diese Spalten mappen.
Die exakten Feldnamen hängen vom Download-Format ab — deshalb zuerst Teil 1.

### 2c: Zeitreihen (optional, für Premium-Report)

Falls der EGMS-Datensatz Zeitreihen enthält (displacement pro Datum pro Punkt),
importiere diese in `egms_timeseries`:

```sql
point_id BIGINT REFERENCES egms_points(id),
measurement_date DATE NOT NULL,
displacement_mm REAL NOT NULL,
PRIMARY KEY (point_id, measurement_date)
```

Das ist optional für den MVP. Zeitreihen machen den Report aber deutlich wertvoller
("Ihr Gebäude senkt sich seit 2018 beschleunigt").

### 2d: Requirements

Falls zusätzliche Python-Packages nötig sind (z.B. `geopandas`, `fiona` für GeoPackage),
füge sie zu einer separaten `backend/scripts/requirements-import.txt` hinzu.
NICHT zu den Haupt-Requirements — das Import-Script läuft einmalig, nicht im API-Server.

---

## Erwartetes Ergebnis

1. `docs/EGMS_DATA_REPORT.md` mit allen Antworten aus Teil 1
2. `backend/scripts/import_egms.py` das funktioniert
3. Testlauf: Import einer Region, dann `SELECT COUNT(*) FROM egms_points` zeigt > 0
4. Testlauf: `SELECT COUNT(*) FROM egms_points WHERE ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(4.4777, 51.9244), 4326)::geography, 500)` zeigt Punkte für Rotterdam Centraal

---

## Was NICHT gemacht werden soll

- Keine Änderungen an `reports.py`, `models.py`, `schemas.py`, Frontend oder sonstigem Code
- Kein Re-Design der DB-Tabelle — die Struktur steht und wird von der API erwartet
- Keine Mock-Daten generieren — nur echte EGMS-Daten importieren
