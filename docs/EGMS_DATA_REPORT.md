# EGMS Data Report (Rotterdam + Ruhrgebiet)

Datum: 2026-04-12  
Quelle: offizieller EGMS Viewer (`https://egms.land.copernicus.eu/`)  
Produkt: **ORTHO (Level 3), Vertical, 2019-2023** (`EGMS-ORTHO-U-U3-release`)

## Kurzfazit

- Die Punktdichte in **urbanen 500m-Radien** ist gut bis sehr gut (typisch ~75-79 Punkte in den getesteten Zentren).
- In **Vororten** sinkt die Dichte deutlich (z. B. 44 Punkte im Bochumer Ostrand).
- In **ländlichen Bereichen** kann die Dichte sehr niedrig sein (6-7 Punkte in 500m).
- Damit ist die Auflösung fuer Adress-Reports in Stadtlagen solide, auf dem Land aber teils grenzwertig.

---

## 1) Download / Datenzugang

### Was wurde technisch geladen

Die EGMS-Weboberflaeche liefert die Daten als Tile-Streams im Format `object/ngv` (NG3d-Container), z. B.:

- `https://egms.land.copernicus.eu/object-layer/EGMS-ORTHO-U-U3-release/{lod}/{x}/{y}/0`

Fuer Rotterdam + Ruhrgebiet wurden 18 Tiles (3x3 + 3x3 Neighborhood) angefragt, davon 17 erfolgreich mit Daten geladen.

- Geladene Datenmenge: **3,225,812 Bytes** (~3.08 MiB)
- Punkte in diesen geladenen Tiles (gesamt): **115,040**

> Hinweis: Der klassische Archiv-Download (`egms-archive-links.txt` mit CSV-Zips) erfordert Login im EGMS-Explorer. Fuer diese Analyse wurden die echten Live-Tiles aus dem offiziellen Viewer verwendet.

---

## 2) Struktur / Format / Felder

### Dateiformat

- Live-Tile-Format: **NG3d / object-ngv** (binär, chunk-basiert)
- Typische Chunks:
  - `cntr` (Tile-Zentrum, 3x float64)
  - `vtx` (Punkt-Offsets, float32)
  - `prop` (Punkt-Property-Wert, float32)
  - `ipid` (Punkt-IDs, 64-bit)
  - `Sabx`, `ENUb`, `colr`, `pnme`, `Stls`

### Felder / Datentypen (im untersuchten L3 Vertical Stream)

- `Mean velocity` (`prop`) -> `float32` (mm/Jahr)
- Punkt-ID (`ipid`) -> 64-bit Integer
- Geometrie -> aus `cntr + vtx` rekonstruiert; danach in WGS84 (`lat/lon`) umgerechnet

### Koordinaten / CRS

- Intern im Stream: globe/cartesian (NG3d interne Darstellung)
- Fuer Analyse in geographische Koordinaten umgerechnet (`lat/lon` in WGS84-Logik)
- Offizielles EGMS L3 Produkt ist ein 100m-Grid in ETRS89/LAEA (EPSG:3035); Viewer liefert die Darstellung tile-basiert.

### Gibt es `mean_velocity`, `velocity_std`, `coherence`?

- `mean_velocity`: **ja** (als `Mean velocity`)
- `velocity_std`: **nicht im L3-Viewer-Tilestream sichtbar**
- `coherence`: **nicht im L3-Viewer-Tilestream sichtbar**

### Zeitreihen vorhanden?

- Im Tile-Stream selbst nicht als Spalten enthalten.
- In der Produkt-Metadatenstruktur ist Plot/Timeseries vorhanden (Einheiten: `timestamp`, `mm`), d. h. zeitliche Informationen sind im EGMS-Stack vorhanden, aber nicht direkt in den geladenen L3-Tile-Punktfeldern.

---

## 3) Dichteanalyse (500m-Radius)

Formel:
- Flaeche(500m-Radius) = pi * 0.5^2 = 0.785 km²
- Punkte/km² = Punkte_500m / 0.785

### Testpunkte

| Standort | Koordinate | Punkte in 500m | Punkte/km² |
|---|---:|---:|---:|
| Rotterdam Centrum | 51.9244, 4.4777 | **79** | **100.59** |
| Rotterdam Vorort (Capelle) | 51.9300, 4.5800 | **75** | **95.49** |
| NL Land (bei 52.0000, 4.9000) | 52.0000, 4.9000 | **6** | **7.64** |
| Ruhrgebiet Zentrum (Essen) | 51.4556, 7.0116 | **77** | **98.04** |
| Ruhrgebiet Vorort (Bochum Ost) | 51.4900, 7.2800 | **44** | **56.02** |
| DE Land (bei 51.6500, 7.9500) | 51.6500, 7.9500 | **7** | **8.91** |

### Antwort auf die Kernfrage

- **Stadtlagen:** 75-79 Punkte im 500m-Radius -> statistisch gut fuer einen Report.
- **Vororte:** 44-75 Punkte -> nutzbar, aber variabler.
- **Land:** 6-7 Punkte -> fuer robuste Adressbewertung haeufig zu duenn.

---

## 4) Qualitaet / Wertebereich (aus den Testradien)

Gepoolte Stichprobe ueber alle 6 Testradien:

- n = **288** Punkte
- |velocity| min = **0.30 mm/a**
- |velocity| max = **9.80 mm/a**
- mean = **1.78 mm/a**
- median = **1.40 mm/a**
- Q1 = **1.10 mm/a**
- Q3 = **1.70 mm/a**
- IQR-Outlier (1.5*IQR) = **43**

NULL-Werte:
- In den selektierten Punktstichproben wurden keine NULL-Velocitywerte im Stream beobachtet.

---

## 5) Bewertung fuer GeoForensic-Reports

### Reicht die Aufloesung?

**Ja, fuer urbane und viele suburbane Adressen.**  
**Eingeschraenkt fuer laendliche Adressen.**

Empfohlene Regel fuer den Report-Status:

- >= 50 Punkte in 500m -> solide
- 20-49 Punkte -> eingeschraenkt belastbar
- < 20 Punkte -> niedrige Belastbarkeit / Hinweis im Report erforderlich

---

## 6) Konsequenz fuer Import

- Fuer die produktive Pipeline sollten die offiziellen EGMS-Archive (CSV/GPKG) importiert werden.
- Das Import-Script wurde erstellt: `backend/scripts/import_egms.py`
- Unterstuetzt:
  - CSV und GeoPackage
  - CRS-Transformation auf EPSG:4326 (bei GPKG)
  - Batch-Import (Standard 10,000)
  - Progress-Ausgabe
  - Duplikat-Pruefung via `WHERE NOT EXISTS`
