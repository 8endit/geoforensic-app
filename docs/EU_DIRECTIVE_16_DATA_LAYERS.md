# EU Soil Monitoring Directive (2025/2360) — 16 Pflichtdaten & Datenquellen

**Stand:** 12.04.2026 | **Directive in Kraft seit:** 16.12.2025 | **Umsetzungsfrist:** 17.12.2028

---

## Übersicht

| # | Descriptor | Annex | API verfügbar? | Integration |
|---|---|---|---|---|
| 1 | Soil Organic Carbon | Part A | ✅ REST API | Sofort |
| 2 | Erosion (Wasser) | Part A | ❌ Download | 1 Woche |
| 3 | Compaction (Oberboden) | Part A | ✅ REST API | Sofort |
| 4 | Compaction (Unterboden) | Part A | ✅ REST API | Sofort |
| 5 | Schwermetalle | Part A | ✅ ArcGIS REST | Sofort |
| 6 | Nährstoffe (N) | Part B | ✅ REST API | Sofort |
| 7 | Versalzung | Part B | ❌ Download | 1 Woche |
| 8 | Versauerung (pH) | Part B | ✅ REST API | Sofort |
| 9 | Biodiversität | Part B | ❌ Download | 2 Wochen |
| 10 | PFAS | Part C | ⚡ Bulk CSV + EEA Discodata API | 1 Woche |
| 11 | Pestizide | Part C | ⚡ EEA Discodata API + ESDAC Download | 1 Woche |
| 12 | Microplastics | Part C | ❌ Keine Daten | Nicht möglich |
| 13 | Versiegelung | Part D | ✅ WMS | Sofort |
| 14 | Bodenentnahme | Part D | ✅ WMS | 1 Woche |
| 15 | Altlastenkataster | Art. 17 | 🟡 Pro Bundesland | Mittel |
| 16 | Georef. Boden-DB | Art. 17 | ❌ Existiert nicht | Ab ~2035 |

---

## Part A — EU-weite Schwellenwerte

### #1 Soil Organic Carbon (SOC)

**Quelle:** SoilGrids v2.0 (ISRIC)
**Lizenz:** CC-BY 4.0
**Auflösung:** 250m global
**API-Typ:** REST (JSON)

```
GET https://rest.isric.org/soilgrids/v2.0/properties/query
  ?lon={lon}&lat={lat}
  &property=soc
  &depth=0-5cm&depth=5-15cm&depth=15-30cm
  &value=mean&value=Q0.05&value=Q0.95
```

**Response:** JSON mit SOC in dg/kg (÷10 = g/kg) pro Tiefenintervall
**Rate Limit:** 5 calls/min
**Docs:** https://rest.isric.org/soilgrids/v2.0/docs
**⚠️ Status April 2026:** REST API intermittent DOWN. WCS-Fallback nutzen (siehe unten).

**Alternativ:** WCS für Raster-Subsets:
```
https://maps.isric.org/mapserv?map=/map/soc.map&SERVICE=WCS&VERSION=2.0.1
  &REQUEST=GetCoverage&COVERAGEID=soc_0-5cm_mean
  &FORMAT=image/tiff&SUBSET=long({lon-0.1},{lon+0.1})&SUBSET=lat({lat-0.1},{lat+0.1})
```

---

### #2 Erosion (Wasser-Erosion / RUSLE)

**Quelle:** ESDAC RUSLE2015
**Lizenz:** Frei nach Registrierung (nicht-kommerziell)
**Auflösung:** 100m, EU-Abdeckung
**API-Typ:** ❌ Kein API — nur GeoTIFF-Download

**Download:** https://esdac.jrc.ec.europa.eu/content/soil-erosion-water-rusle2015
(Registrierung bei ESDAC erforderlich)

**Daten:** Bodenverlust in t/ha/yr + Einzelfaktoren (R, K, LS, C, P)

**Integration:**
1. GeoTIFF einmalig herunterladen (~500 MB für EU)
2. Mit `rasterio` lokal als Point-Lookup servieren
3. Oder selbst als WMS via GeoServer hosten

**Alternativ (selbst berechnen):**
- R-Faktor: CHIRPS Niederschlagsdaten
- K-Faktor: SoilGrids Textur
- LS-Faktor: Copernicus DEM (Slope + Flow Accumulation)
- C-Faktor: Sentinel-2 NDVI
- P-Faktor: CORINE Landnutzung

---

### #3 + #4 Compaction (Ober- und Unterboden)

**Proxy 1: Bulk Density (SoilGrids)**
**Quelle:** SoilGrids v2.0 (ISRIC)
**Lizenz:** CC-BY 4.0
**Auflösung:** 250m global
**API-Typ:** REST (JSON) + WCS (GeoTIFF)

```
GET https://rest.isric.org/soilgrids/v2.0/properties/query
  ?lon={lon}&lat={lat}
  &property=bdod
  &depth=0-5cm&depth=5-15cm&depth=15-30cm&depth=30-60cm&depth=60-100cm
  &value=mean
```

**Response:** Bulk Density in cg/cm³ (÷100 = g/cm³). Höhere Werte = stärkere Verdichtung.
Typische Schwellen: >1.6 g/cm³ = verdichtet (toniger Boden), >1.8 g/cm³ = stark verdichtet (sandiger Boden).

**WCS Fallback:**
```
https://maps.isric.org/mapserv?map=/map/bdod.map&SERVICE=WCS&VERSION=2.0.1
  &REQUEST=GetCoverage&COVERAGEID=bdod_0-5cm_mean
  &FORMAT=image/tiff&SUBSET=long({lon-0.1},{lon+0.1})&SUBSET=lat({lat-0.1},{lat+0.1})
```

**Proxy 2: InSAR Bodenbewegung (EGMS)**
Setzungsrate als Indikator für Compaction-bedingte Konsolidierung.
Quelle: EGMS L3 Ortho (Sentinel-1), bereits in Report-Pipeline integriert.
Kein API — lokale DB-Query (PostGIS).

---

### #5 Schwermetalle (Cd, Pb, Hg, As, Cr, Cu, Ni, Zn)

**Quelle:** BGR (Bundesanstalt für Geowissenschaften und Rohstoffe)
**Lizenz:** dl-de/by-2-0 (Datenlizenz Deutschland)
**Auflösung:** 1:1.000.000
**API-Typ:** ArcGIS REST (JSON)
**Abdeckung:** Deutschland

```
GET https://services.bgr.de/arcgis/rest/services/boden/bodenstoffe/MapServer/identify
  ?geometry={lon},{lat}
  &geometryType=esriGeometryPoint
  &sr=4326
  &layers=all:4
  &tolerance=1
  &mapExtent=5,47,16,56
  &imageDisplay=800,600,96
  &returnGeometry=false
  &f=json
```

**Verfügbare Elemente (16):** As, Be, Cd, Co, Cr, Cu, Hg, Mo, Ni, Pb, Sb, Se, Tl, U, V, Zn
Jeweils in 3 Tiefen: Oberboden, Unterboden, Untergrund (Layer-IDs 1-64)

**Layer-IDs (Auswahl Directive-relevant):**
| Element | Oberboden | Unterboden |
|---|---|---|
| As | 1 | 2 |
| Cd | 7 | 8 |
| Cr | 13 | 14 |
| Cu | 16 | 17 |
| Hg | 22 | 23 |
| Ni | 28 | 29 |
| Pb | 31 | 32 |
| Zn | 61 | 62 |

**WMS alternativ:**
```
https://services.bgr.de/wms/boden/hgw1000/?SERVICE=WMS&REQUEST=GetCapabilities
```

**EU-weit (geringere Auflösung):**
- GEMAS (1 Probe / 2500 km²) — zu grob für Standort-Reports
- ESDAC Heavy Metals Maps (1 km, Kriging) — nur Download nach Registrierung

---

## Part B — Mitgliedsstaaten-Schwellenwerte

### #6 Nährstoffe (Stickstoff N)

**Quelle:** SoilGrids v2.0 (ISRIC)
**Lizenz:** CC-BY 4.0
**Auflösung:** 250m

```
GET https://rest.isric.org/soilgrids/v2.0/properties/query
  ?lon={lon}&lat={lat}
  &property=nitrogen&property=cec
  &depth=0-5cm&depth=5-15cm
  &value=mean
```

**Response:** Nitrogen in cg/kg (÷100 = g/kg), CEC in mmol(c)/kg
**CEC** (Cation Exchange Capacity) als Proxy für Nährstoff-Rückhalt: `&property=cec`

**Phosphor:** ❌ Kein API verfügbar. Optionen:
- LUCAS Topsoil Survey (~22.000 EU-Punkte) — ESDAC-Download nach Registrierung
- WoSIS Punktdatenbank (https://isric.org/explore/wosis) — Einzelmessungen, kein Grid
- NPKGRIDS (Nature Sci Data 2024) — Düngemittel-Input, nicht Bodenstatus

---

### #7 Versalzung (Salinisation)

**Quelle:** ISRIC Global Soil Salinity Rasters
**Lizenz:** Open access
**Auflösung:** 250m
**API-Typ:** ❌ Kein API — GeoTIFF-Download

**Download:** https://files.isric.org/public/global_soil_salinity/
(EC-Werte 1986-2016, GeoTIFF/VRT)

**Alternativ:** FAO GSASmap (1 km) via Google Earth Engine

**Integration:** GeoTIFF herunterladen, lokal mit `rasterio` Point-Lookup.

**Hinweis:** Deutschland ist außerhalb von Küsten- und Bergbauregionen kaum betroffen.

---

### #8 Versauerung (Boden-pH)

**Quelle:** SoilGrids v2.0 (ISRIC)
**Lizenz:** CC-BY 4.0
**Auflösung:** 250m
**API-Typ:** REST (JSON) — **FUNKTIONIERT**

```
GET https://rest.isric.org/soilgrids/v2.0/properties/query
  ?lon={lon}&lat={lat}
  &property=phh2o
  &depth=0-5cm&depth=5-15cm&depth=15-30cm
  &value=mean
```

**Response:** pH × 10 (Integer). Wert 63 = pH 6.3
**Getestet:** lon=10.0, lat=51.0 → pH 6.3 (0-5cm) ✓

---

### #9 Biodiversität (Pilze + Bakterien)

**Quelle:** ESDAC Soil Microbial Diversity Maps (JRC 2023)
**Lizenz:** Frei nach Registrierung
**Auflösung:** ~1 km (interpoliert aus 715 LUCAS-Sites)
**API-Typ:** ❌ Kein API — Download nach Registrierung

**Download:** https://esdac.jrc.ec.europa.eu/themes/soil-microbial-diversity-across-europe

**Daten:** Predicted Maps für:
- Mikrobielle Biomasse (Cmic)
- Basale Respiration
- Respiratorischer Quotient
- ~79.000 bakterielle + ~25.000 pilzliche OTUs

**Proxy via SoilGrids:** SOC als Indikator für mikrobielle Aktivität:
```
GET https://rest.isric.org/soilgrids/v2.0/properties/query?lon={lon}&lat={lat}&property=soc&depth=0-5cm&value=mean
```

**Hinweis:** Die Directive verlangt DNA-Metabarcoding. Kein Satellit/Modell kann das ersetzen. Unsere Rolle: Screening-Proxy + Empfehlung "Laborprobe empfohlen".

---

## Part C — Kontaminanten

### #10 PFAS

**Quelle 1:** Forever Pollution Project (CNRS)
**Lizenz:** Open data (GitLab), ~23.000 Standorte kartiert
**API-Typ:** ⚡ Bulk-Download CSV mit lat/lon von GitLab (pdh.cnrs.fr)
**Karte:** https://foreverpollution.eu/map/

**Integration:** CSV herunterladen, eigenen Spatial Index bauen für Proximity-Queries.

**Quelle 2:** EEA Discodata (Grundwasser-Monitoring)
**API-Typ:** ✅ SQL-over-HTTP → CSV/JSON
```
https://discodata.eea.europa.eu/sql?query=SELECT * FROM [WISE_SoE].[latest].[waterbase_groundwater] WHERE ...
```
Enthält PFOS/PFOA-Messungen an Grundwasser-Stationen. Querybar nach Koordinatennähe.

**Quelle 3:** IPCHEM (JRC) — EU-weite Chemikalien-Plattform
**API-Typ:** Python/R Library (`ipchem.jrc.ec.europa.eu`)

**Offiziell (Zukunft):**
- EU Directive Art. 17: georeferenziertes Register bis 2035
- ECHA PFAS-Beschränkung: RAC-Opinion März 2026, SEAC bis Mai 2026, Entscheidung ~2028
- Ab 13.01.2026: Trinkwasser-PFAS-Grenzwerte in allen MS

**UBA (Deutschland):** Kein öffentliches PFAS-Bodenregister. Soil-Monitoring-Projekt 2026-2029 geplant.

---

### #11 Pestizide + Metaboliten

**Quelle 1:** ESDAC LUCAS 2018 Pesticide Residues
**Lizenz:** Frei nach Registrierung
**Auflösung:** NUTS2-Ebene (DSGVO-bedingt anonymisiert)
**API-Typ:** ❌ Download nach Registrierung

**Download:** https://esdac.jrc.ec.europa.eu/themes/pesticides-residues-eu-agricultural-soils-based-lucas

**Daten:** 118 Wirkstoffe an 3.473 EU-Standorten, Konzentration in mg/kg
- 74,5% der Agrarflächen enthalten Pestizid-Rückstände
- 57,1% enthalten Mischungen mehrerer Pestizide

**Quelle 2:** EEA Discodata (Grundwasser-Monitoring)
**API-Typ:** ✅ SQL-over-HTTP (gleicher Endpunkt wie PFAS)
Enthält Pestizid-Messungen an Grundwasser-Stationen (WFD-Reporting).

**Quelle 3:** BGR Grundwasser-Pestizid-Datenbank (DE)
521 Wirkstoffe + Metaboliten an 26.192 Messstellen (1973-2021).
**API-Typ:** ❌ Statischer Forschungsdatensatz (Cooke et al., 2024), kein Live-API.

**Integration:** EEA Discodata als API für Wasser-Nähe-Query. ESDAC als regionaler Hintergrund.
NUTS2-Auflösung ist für Adress-Reports zu grob → als Kontext: "Ihre Region hat hohe/niedrige Pestizidbelastung".

---

### #12 Organische Kontaminanten (PAK, PCB, BTEX, Dioxine)

**Quelle 1:** EEA Discodata — PAH, PCB in Gewässern querybar (gleicher Endpunkt)
**Quelle 2:** IPCHEM (JRC) — Environmental Monitoring Module, Python/R Library
**Quelle 3:** Altlastenkataster pro Bundesland (siehe #15)

**Status:** Kein einheitlicher EU-Boden-Datensatz.
Wasser-Daten querybar via EEA Discodata. Boden-Daten nur in Altlastenregistern.

**Zukunft:** EU Directive Art. 17 wird dies ab ~2030 standardisieren.
Indicative Contaminant List der Kommission erwartet Mitte 2027.

---

### #13 Microplastics

**Status:** ❌ Keine operationellen Bodendaten verfügbar.

- Nur Forschungsprojekte (z.B. JRC 2023: erste EU-weite Abschätzung)
- Kein Monitoring-Standard definiert
- Directive nennt Microplastics, aber Mess-Methodik wird erst entwickelt

**Integration:** Nicht möglich. Im Report als "Daten noch nicht verfügbar (EU-Monitoring ab ~2030)" vermerken.

---

## Part D — Versiegelung + Bodenentnahme

### #14 Versiegelung (Soil Sealing / Imperviousness)

**Quelle:** Copernicus HRL Imperviousness Density (IMD)
**Lizenz:** Copernicus open access
**Auflösung:** 10m (2018/2021)
**API-Typ:** ✅ WMS (OGC)

```
https://image.discomap.eea.europa.eu/arcgis/services/GioLandPublic/HRL_ImperviousnessDensity_2018/ImageServer/WMSServer
  ?SERVICE=WMS&VERSION=1.3.0
  &REQUEST=GetFeatureInfo
  &LAYERS=0
  &CRS=EPSG:4326
  &BBOX={lat-0.001},{lon-0.001},{lat+0.001},{lon+0.001}
  &WIDTH=1&HEIGHT=1
  &QUERY_LAYERS=0
  &I=0&J=0
  &INFO_FORMAT=application/json
```

**Response:** Imperviousness Density 0-100% an Koordinate

**REST Browse:** https://image.discomap.eea.europa.eu/arcgis/rest/services/GioLandPublic

**Versionen:** 2006, 2009, 2012, 2015, 2018, 2021 — Zeitreihe möglich!

---

### #15 Bodenentnahme (Land Take / Soil Removal)

**Quelle:** CORINE Land Cover Change Layers
**Lizenz:** Copernicus open access
**Auflösung:** 100m / 25 ha MMU (change: 5 ha)
**API-Typ:** ✅ WMS

```
https://image.discomap.eea.europa.eu/arcgis/services/Corine/CHA2012_2018_WM/MapServer/WMSServer
  ?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetFeatureInfo
  ...
```

**Land Take Logik:** Change von natürlichen/landwirtschaftlichen Klassen → künstliche Flächen (CLC 1.x.x)

**Neu:** CLC+ Backbone (10m, Sentinel-2 basiert) ab 2021 verfügbar.

---

## Art. 17 — Register

### #16 Kontaminierte Standorte (Altlastenkataster)

**Status:** ❌ Kein bundesweites API. Pro Bundesland unterschiedlich.

| Bundesland | WMS verfügbar? | Endpunkt |
|---|---|---|
| **Niedersachsen** | ✅ JA | `https://nibis.lbeg.de/net3/public/ogc.ashx?PkgId=27&Service=WMS&Request=GetCapabilities` |
| NRW | ❌ Nein | FIS AlBo nur für Behörden (LANUV intern) |
| Bayern | ❌ Nein | ABuDIS 3.0 nur für Behörden (LfU intern) |
| Baden-Württemberg | ❌ Nein | LUBW — kein öffentlicher Altlasten-Layer |
| Andere Länder | 🟡 Unklar | Einzelfallprüfung nötig |

**EU-weit:** EEA sammelt nur aggregierte Statistiken, nicht georeferenziert.

**Zukunft:** Directive Art. 17 → öffentliches georeferenziertes Register bis 17.12.2035

### #17 Georeferenzierte öffentliche Boden-DB

**Status:** Existiert noch nicht.
- ESDAC Map Viewer seit 2020 offline
- SoilWise-HE (Horizon Europe) baut neue Infrastruktur, noch in Entwicklung
- Directive erzwingt nationale DBs bis 2028 (Transposition) / 2035 (Daten)

---

## Zusammenfassung: Integration-Roadmap

### Sofort integrierbar (REST API vorhanden)

| # | Descriptor | API-Call |
|---|---|---|
| 1 | SOC | `rest.isric.org/soilgrids/…?property=soc` |
| 3+4 | Compaction (Bulk Density) | `rest.isric.org/soilgrids/…?property=bdod` |
| 5 | Schwermetalle (DE) | `services.bgr.de/arcgis/rest/…/identify` |
| 6 | Stickstoff | `rest.isric.org/soilgrids/…?property=nitrogen` |
| 8 | pH | `rest.isric.org/soilgrids/…?property=phh2o` |
| 13 | Versiegelung | `image.discomap.eea.europa.eu/…/WMSServer` |

**→ 7 von 16 Descriptors mit einem einzigen HTTP GET pro Adresse.**

### Download + lokaler Lookup (1-2 Wochen Aufwand)

| # | Descriptor | Download-Quelle |
|---|---|---|
| 2 | Erosion (RUSLE) | ESDAC GeoTIFF |
| 7 | Versalzung | ISRIC GeoTIFF |
| 9 | Biodiversität | ESDAC Raster |
| 11 | Pestizide | ESDAC LUCAS CSV |
| 14 | Bodenentnahme | CORINE Change WMS + CLC+ |

### Langfristig / Register (ab 2030-2035)

| # | Descriptor | Warauf warten? |
|---|---|---|
| 10 | PFAS | Nationale Register + Forever Pollution Project |
| 12 | Microplastics | Mess-Methodik noch in Entwicklung |
| 15 | Altlastenkataster | Pro-Bundesland-Erschließung |
| 16 | EU Boden-DB | Directive-Umsetzung bis 2035 |

---

## Technische Architektur

```
Adresse → Geocoding (Nominatim)
    ↓
Koordinate (lat, lon)
    ↓
┌─────────────────────────────────────────────┐
│ Parallele Abfragen:                         │
│                                             │
│  SoilGrids REST → SOC, pH, N, Bulk Density │
│  BGR ArcGIS REST → Schwermetalle (8 Elemente)│
│  EGMS PostGIS → InSAR Velocity + Zeitreihe  │
│  Copernicus WMS → Versiegelung (IMD)         │
│  CORINE WMS → Landnutzung + Change           │
│  Lokale GeoTIFFs → Erosion, Salinity, Bio    │
│  Altlasten WMS → Niedersachsen (wo verfügbar)│
│  Forever Pollution → PFAS Nähe               │
└─────────────────────────────────────────────┘
    ↓
Aggregation → GeoScore (0-100) + Ampel
    ↓
PDF Report + API Response
```

---

## Quellen

- SoilGrids REST API: https://rest.isric.org/soilgrids/v2.0/docs
- SoilGrids WMS/WCS: https://maps.isric.org
- BGR Bodenstoffe: https://services.bgr.de/arcgis/rest/services/boden/bodenstoffe/MapServer
- ESDAC Datasets: https://esdac.jrc.ec.europa.eu/resource-type/datasets-list
- ESDAC RUSLE2015: https://esdac.jrc.ec.europa.eu/content/soil-erosion-water-rusle2015
- Copernicus IMD: https://land.copernicus.eu/en/products/high-resolution-layer-imperviousness
- EEA DiscoMap: https://image.discomap.eea.europa.eu/arcgis/rest/services/GioLandPublic
- CORINE Land Cover: https://land.copernicus.eu/en/products/corine-land-cover
- ISRIC Salinity: https://files.isric.org/public/global_soil_salinity/
- ESDAC Biodiversity: https://esdac.jrc.ec.europa.eu/content/global-soil-biodiversity-maps-0
- ESDAC Pesticides: https://esdac.jrc.ec.europa.eu/themes/pesticides-residues-eu-agricultural-soils-based-lucas
- Forever Pollution (PFAS): https://foreverpollution.eu/map/
- Niedersachsen Altlasten: https://nibis.lbeg.de/net3/public/ogc.ashx?PkgId=27
- EU Directive 2025/2360: https://eur-lex.europa.eu/eli/dir/2025/2360/oj/eng
- BGR-APIs (Node.js Wrapper): https://github.com/fruchtfolge/BGR-APIs
- FAO Salt-Affected Soils: https://www.fao.org/soils-portal/data-hub/soil-maps-and-databases/global-map-of-salt-affected-soils/en/
- EEA Discodata: https://discodata.eea.europa.eu
- IPCHEM (JRC): https://ipchem.jrc.ec.europa.eu
- NISAR Data: https://science.nasa.gov/mission/nisar/data/
- Sentinel-1C/D Status: https://sentinels.copernicus.eu/-/sentinel-1d-user-data-opening-and-future-plans
