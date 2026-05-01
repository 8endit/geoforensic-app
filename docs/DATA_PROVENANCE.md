# DATA_PROVENANCE.md — Datenquellen-Audit für Bodenbericht und Vollbericht

**Stand:** 2026-04-30, nach ProofTrailAgents-Migration (Phase A).
**Zweck:** Einzige verbindliche Wahrheit, woher jeder Datenpunkt im Report
kommt, welche Lizenz er hat und welche Modell-Schätzungen wir wo einsetzen.
Der Report-PDF zitiert pro Sektion die hier dokumentierte Quelle wörtlich.

**Verifizierungs-Skala:**
- **VERIFIZIERT** — Endpunkt + Lizenz + Layer-Strings aus mindestens zwei
  unabhängigen Quellen oder direkt geprüft, läuft im Code mit Echtdaten
- **TEILWEISE** — Datenquelle integriert, aber ein Aspekt offen (Lizenz noch
  unbestätigt, Layer-Namen Best-Guess, Coverage limitiert)
- **GEPLANT** — Modul vorbereitet, Daten ausstehend (User muss anfordern oder
  hochladen), läuft aktuell auf Fallback

---

## 1. Bodenbewegung — InSAR

### 1.1 EGMS (European Ground Motion Service)

| Feld | Wert |
|---|---|
| **Status** | VERIFIZIERT, live |
| Datensatz | EGMS L2a/L3 Persistent Scatterers, Vertical + East-West |
| Quelle | Copernicus Land Monitoring Service |
| Portal | <https://egms.land.copernicus.eu/> |
| Bezugszeitraum | 2019–2023 (T1-Release) |
| Coverage | EU + UK + Schweiz + Norwegen |
| Granularität | Punktwolke (~50–80 Punkte / 500 m in DE-Wohngebieten) |
| Lizenz | Copernicus Free, Full, Open Data License (CC BY 4.0) |
| Attribution | „Generated using European Union's Copernicus Land Monitoring Service information" |
| Persistenz | PostGIS Tabelle `egms_points`, 7,9 Mio Punkte DE/NL/AT/CH |
| Modul | `backend/app/main.py` (DB-Query in Pipeline) |

### 1.2 BGR BBD (Bodenbewegungsdienst Deutschland)

| Feld | Wert |
|---|---|
| **Status** | GEPLANT — Lizenz-Mail an `BBD@bgr.de` ausstehend |
| Erwarteter Mehrwert | +30–40 % Messpunkte gegenüber EGMS in DE |
| Vorlage | `docs/MAIL_BGR_BBD.md` |

---

## 2. Boden — physikalisch / chemisch

### 2.1 SoilGrids 250 m

| Feld | Wert |
|---|---|
| **Status** | VERIFIZIERT, live |
| Datensatz | 6 Variablen × 0–30 cm: SOC, pH, BD, Clay, Sand, Silt |
| Quelle | ISRIC World Soil Information |
| Portal | <https://soilgrids.org> |
| Lizenz | CC BY 4.0 |
| Attribution | „SoilGrids 250m by ISRIC, CC BY 4.0" |
| Pixelpfad F: | `soilgrids_<prop>_0-30cm_nlde.tif` (NL+DE, bevorzugt) |
| Pixelpfad Fallback | `soilgrids_<prop>_0-30cm.tif` (DE-only) |
| Bounds nlde | 3,3 °E – 15,1 °E / 47,2 °N – 55,2 °N |
| Skalierung | siehe `SOILGRIDS_PROPERTIES` in `backend/app/soil_data.py:60` |
| Modul | `backend/app/soil_data.py` |
| Caveat | Urbane SoilGrids-Werte sind teils unplausibel (Klassifikator-Artefakt; städtische Auflagen). Im Report als „Schätzung Bodenparameter, regional kalibriert" deklarieren. |

### 2.2 LUCAS Topsoil — Schwermetalle und Nährstoffe (DE)

| Feld | Wert |
|---|---|
| **Status** | VERIFIZIERT, live |
| Datensatz | Heavy metals (Cd, Pb, Hg, As, Cr, Cu, Ni, Zn) + P + N_total |
| Quelle | JRC European Soil Data Centre (ESDAC) |
| Portal | <https://esdac.jrc.ec.europa.eu/projects/lucas> |
| Lizenz | EU Open Data, kommerziell OK mit Attribution |
| Coverage | DE — 3 000 Punkte; NL hat in unserer CSV keine Punkte |
| Lookup | KD-Tree IDW über 3 nächste Nachbarn |
| Pixelpfad F: | `lucas_soil_de.csv` |
| Modul | `backend/app/soil_data.py` (`LucasLookup`) |
| Caveat | NL-Adressen erhalten LUCAS-Werte aus ≥50 km Entfernung — Modul flaggt das per `lucas_distance_km`-Feld; Vollbericht muss bei Distanz > 50 km „nicht standortspezifisch" zeigen. |

### 2.3 LUCAS Topsoil 2018 — Pestizid-Rückstände (NUTS2)

| Feld | Wert |
|---|---|
| **Status** | VERIFIZIERT, live |
| Datensatz | 118 Aktivsubstanzen + Metaboliten, NUTS2-aggregiert |
| Quelle | JRC ESDAC, LUCAS Pesticides 2018 |
| Portal | <https://esdac.jrc.ec.europa.eu/projects/lucas> |
| Lizenz | EU Open Data |
| Pixelpfad F: | `lucas_pesticides_nuts2.xlsx` |
| Modul | `backend/app/pesticides_data.py` |
| Granularität | NUTS2-Region (kein Punkt-Wert) |
| Spatial-Lookup | Eurostat GISCO NUTS-2021 GeoJSON (siehe §6.1) |
| Reporting-Pflicht | Sektion muss „Regionaler Pestizid-Befund (NUTS2-Gebiet)" heißen — NICHT „Ihr Grundstück" |
| Threshold-Hinweis | Keine direkten BBodSchV-Bodenschwellenwerte für moderne Pestizide; EU-Trinkwasser 0,1 µg/L als Größenordnungs-Kontext |
| Legacy-Flagging | DDT/Aldrin/Endrin/Atrazine/Chlorpyrifos etc. werden separat hervorgehoben |

### 2.4 Heavy-Metal-Schwellenwerte — DE / NL / Default

| Feld | Wert |
|---|---|
| **Status** | VERIFIZIERT (gesetzliche Grundlagen, hardcoded), **country-geroutet** |
| Substanzen | Cd, Pb, Hg, As, Cr, Cu, Ni, Zn |

**DE — BBodSchV §8 Anhang 2** (Vorsorge / Maßnahme, Lehm/Schluff)

Kommt zum Einsatz wenn `country_code == "de"` (oder als Default für AT/CH/unbekannt — konservativ).

**NL — Circulaire bodemsanering 2013, Bijlage 1** (Streefwaarde / Interventiewaarde, standaardbodem 25 % lutum / 10 % organische stof)

Kommt zum Einsatz wenn `country_code == "nl"`. Streefwaarde = niveau ohne nennenswerte Risiken; Interventiewaarde = ernstige Verunreinigung, Sanierung erforderlich. Quelle: <https://wetten.overheid.nl/BWBR0033592/>.

**Routing-Modul:** `backend/app/soil_data.py:get_thresholds(country_code)`

**Caveat im Report:** Pro Schwelle wird `metals_threshold_source` mitgeliefert und im PDF wörtlich zitiert. NL-Adressen sehen Streefwaarde-Vergleiche, niemals BBodSchV.

### 2.5 LUCAS Country-Gate

| Feld | Wert |
|---|---|
| **Status** | VERIFIZIERT, live |
| Regel | LUCAS-Schwermetalle und LUCAS-Nährstoffe werden **nur** für `country_code == "de"` ausgeliefert. NL/AT/CH bekommen leere Dicts mit explizitem Note „Schwermetalle aus LUCAS-Boden für diese Region nicht standortspezifisch verfügbar." |
| Begründung | Unsere LUCAS-CSV enthält nur DE-Punkte. Für NL-Adressen liegt der nächste Punkt typischerweise > 200 km entfernt — IDW-Werte aus Brandenburg an Rotterdamer Adressen wären irreführend. |
| Zusätzliche Schranke | `max_distance_km=50` Cap auch für DE — sichert dass entlegene DE-Standorte (Inseln, Grenzregionen) ehrlich „n/a" zurückbekommen statt aus weiter Ferne interpoliert |
| Modul | `backend/app/soil_data.py:SoilDataLoader.query_metals/_nutrients` |

---

## 3. Hochwasser / Wasser

### 3.1 BfG HWRM Hochwassergefahrenkarten

| Feld | Wert |
|---|---|
| **Status** | TEILWEISE — Endpunkte vom VPS verifiziert (Commit `2bd4e36`), Layer-Namen "0" pro ArcGIS-Service. Dokumentation `docs/DATA_SOURCES_VERIFIED.md` muss von TEILW. auf VERIFIZIERT angehoben werden. |
| Datensatz | HQ häufig (T 5–20 a), HQ100 (T 100 a), HQ extrem (≈ 1,5×HQ100) |
| Quelle | Bundesanstalt für Gewässerkunde (BfG), HWRM-RL 2. Zyklus 2016–2021 |
| Endpunkte | drei separate ArcGIS-Services (`HWRMRL_DE_S{L,M,H}/MapServer/WMSServer`) |
| Lizenz | DL-DE/Zero-2.0 (kein Copyleft, kommerziell OK ohne Attribution-Pflicht) |
| Coverage | DE bundesweit, aus Länder-Meldungen aggregiert |
| Modul | `backend/app/flood_data.py` |

### 3.2 DWD KOSTRA-2020 (Starkregen)

| Feld | Wert |
|---|---|
| **Status** | TEILWEISE — Modul integriert, **Raster fehlen noch auf VPS** (`/opt/bodenbericht/rasters/kostra_dwd_2020/`) |
| Datensatz | KOSTRA-DWD-2020 Niederschlagshöhen, Dauerstufen 5 min – 72 h, T = 1, 2, 5, 10, 20, 30, 50, 100 a |
| Quelle | Deutscher Wetterdienst |
| Lizenz | GeoNutzV (kommerziell OK mit Quellenangabe) |
| Attribution | „Deutscher Wetterdienst, KOSTRA-DWD-2020, DOI 10.5676/DWD/KOSTRA-DWD-2020" |
| Modul | `backend/app/kostra_data.py`, Pull-Script `backend/scripts/download_kostra.py` |

---

## 4. Landnutzung / Bodenversiegelung

### 4.1 CORINE Land Cover 2018 (CLC2018 v2020_20u1)

| Feld | Wert |
|---|---|
| **Status** | VERIFIZIERT, live (NEU 2026-04-30) |
| Datensatz | 44 Level-3-Klassen, 100 m Raster |
| Quelle | Copernicus Land Monitoring Service / EEA |
| Portal | <https://land.copernicus.eu/en/products/corine-land-cover> |
| Original-Datei | `U2018_CLC2018_V2020_20u1.tif` (EU-weit, EPSG:3035, 3 GB) |
| Reprojiziert F: | `corine_2018_clc_100m_de_nl.tif` (DE+NL, EPSG:4326, 11 MB, 90 % Coverage) |
| Reprojection-Script | `backend/scripts/reproject_corine.py` |
| Lizenz | Copernicus Free, Full, Open Data Licence |
| Attribution | „© European Union, Copernicus Land Monitoring Service, EEA" |
| Pixel-Codierung | int8-Indices 1–44, Mapping über `CORINE_INDEX_TO_CODE` in `backend/app/soil_data.py:90` auf 3-stellige CLC-Codes 111–523 |
| Modul | `backend/app/soil_data.py` (`SoilDataLoader.query_corine`) |

### 4.2 OSM Overpass — Landuse-Fallback

| Feld | Wert |
|---|---|
| **Status** | VERIFIZIERT, live als Fallback |
| Verwendung | Wird nur aktiviert, wenn CORINE-Raster für eine Adresse NoData liefert (z. B. außerhalb DE+NL Bbox) |
| Quelle | OpenStreetMap Overpass-API |
| Endpunkte | `overpass-api.de/api/interpreter` + `overpass.kumi.systems/api/interpreter` (Failover) |
| Lizenz | ODbL 1.0 |
| Attribution | „© OpenStreetMap contributors, ODbL" |
| Modul | `backend/app/soil_data.py:_query_overpass_landuse` |
| Caveat | Im Report als `source: "osm-overpass"` ausgewiesen — andere Granularität als CORINE |

### 4.3 HRL Imperviousness 20 m

| Feld | Wert |
|---|---|
| **Status** | VERIFIZIERT, live |
| Datensatz | Versiegelungsgrad 0–100 % auf 20 m Raster |
| Quelle | Copernicus Land Monitoring Service, High Resolution Layer |
| Portal | <https://land.copernicus.eu/pan-european/high-resolution-layers/imperviousness> |
| Pixelpfad F: | `hrl_imperviousness_20m.tif` |
| Bounds | 5,8 °E – 15,1 °E / 45,4 °N – 57,0 °N (DE + Streifen NL) |
| Lookup | Window-Mean über 100 m Radius (≈ 11×11 Pixel) — vermeidet Dach-/Straßen-Artefakte |
| Lizenz | Copernicus Free, Full, Open Data Licence |
| Modul | `backend/app/soil_data.py:RasterLookup.query_window_mean` |
| Caveat | NL-Adressen außerhalb der Bounds erhalten None — wird im Report als „nicht verfügbar (DE only)" gezeigt |

---

## 5. Bergbau / Untergrund

### 5.1 NRW Bergbauberechtigungen

| Feld | Wert |
|---|---|
| **Status** | VERIFIZIERT, live |
| Datensatz | Gültige + erloschene Bergbauberechtigungen, Polygone auf Grubenfeld-Ebene |
| Quelle | Bezirksregierung Arnsberg, Geoportal NRW |
| Endpunkt | `https://www.wms.nrw.de/wms/wms_nw_inspire-bergbauberechtigungen` |
| Lizenz | dl-de/by-2.0 |
| Attribution | „Bezirksregierung Arnsberg, dl-de/by-2.0" |
| Coverage | NUR NRW |
| Modul | `backend/app/mining_nrw.py` |

### 5.2 Altlasten / Bodenkontamination

| Feld | Wert |
|---|---|
| **Status** | VERIFIZIERT, country-routed live |
| Modul | `backend/app/altlasten_data.py` |

**NL — PDOK Bodemloket WBB-Lokationen** (echtes Kataster)
- Endpunkt: `https://gis.gdngeoservices.nl/standalone/services/blk_gdn/lks_blk_rd_v1/MapServer/WMSServer`
- Layer: `WBB_locaties`, INFO_FORMAT: `text/xml`
- Lizenz: CC-BY 4.0
- Result-Kennzeichnung im PDF: `data_kind: behoerden-kataster`
- Hinweis: Legacy-URL `service.pdok.nl/rws/bodemloket/` (404 seit 2023) — neue gdn-Endpoints nach Migration

**DE — CORINE-Land-Use-Proxy** (KEIN Kataster!)
- Begründung: LUBW ALTIS (BW) und LANUV FIS AlBo (NRW) sind nach INSPIRE Art 13(1)(f) personenbezogen geschützt — kein public WFS für Open-Data-Lookup.
- Stattdessen: 5-Punkt-Sampling (Adresse + 4 cardinal points ~50 m) gegen `corine_2018_clc_100m_de_nl.tif`. Hits auf den Codes 121/122/123/124/131/132/133 werden als „Kontaminations-Indikator" mit transparenter Begründung pro Code ausgewiesen.
- Result-Kennzeichnung im PDF: `data_kind: land-use-indikator`
- PDF zeigt zusätzlich Hinweis-Block: „Rechtsverbindliche Behördenauskunft anfordern → altlasten@geoforensic.de" (Vorbereitung für späteren Behörden-Vermittlungs-Service als Add-On)

**AT/CH — nicht integriert.**

### 5.3 BGR Geologie GUEK200

| Feld | Wert |
|---|---|
| **Status** | GEPLANT — Modul `geology.py` in ProofTrailAgents, noch nicht migriert (Phase B/C) |
| Quelle | Bundesanstalt für Geowissenschaften und Rohstoffe |
| Endpunkt | BGR GUEK200 WMS GetFeatureInfo |
| Migrationsplan | Phase C, mit dokumentiertem Fallback „nicht verfügbar" |

---

## 6. Geometrie / Spatial Lookups

### 6.1 Geländemodell — Slope und Aspekt

| Feld | Wert |
|---|---|
| **Status** | VERIFIZIERT, live (mit Failover) |
| Modul | `backend/app/slope_data.py` |
| **Primärquelle** | OpenTopoData (`https://api.opentopodata.org/v1/srtm30m`) — frei öffentlich, 1 000 req/day, SRTM 1-arcsec (~30 m horizontal) |
| **Fallback** | Open-Elevation (`https://api.open-elevation.com/api/v1/lookup`) — selbe SRTM-Basis, aktuell flaky (504 beobachtet 2026-04-30) |
| Methode | Multi-Scale-Sampling: Adresse + 4 cardinal probes auf 50 m / 150 m / 500 m → Steepest-Slope per Skala, beste Skala wird gewählt |
| Output | elevation_m, slope_deg, aspect_deg, aspect_label (N/NE/E/SE/S/SW/W/NW), classification (flach / leicht geneigt / Hanglage / Steilhang), scale_m |
| Lizenz | OpenTopoData: ODC-BY 1.0 (für SRTM via NASA, public domain) |
| Reporting-Pflicht | Source-Label im PDF („OpenTopoData (SRTM 1-arcsec)" vs „Open-Elevation API …") |
| Verwendung | (a) eigene Sektion „Geländeprofil" im Vollbericht, (b) `slope_deg` fließt in RUSLE-LS-Faktor in `soil_directive.py` ein — vorher Default 2°, was Hanglagen-Erosion massiv unterschätzte |
| Phase C | NL: AHN WCS (0,5 m LiDAR) ersetzt SRTM. DE: lokale SRTM-Tile-Cache statt Public-API |

### 6.2 NUTS2 Polygone 2021

| Feld | Wert |
|---|---|
| **Status** | VERIFIZIERT, live |
| Datensatz | NUTS-2021 Level-2 Polygone, 334 Regionen EU |
| Quelle | Eurostat GISCO |
| Endpunkt | <https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2021_4326_LEVL_2.geojson> |
| Pixelpfad F: | `nuts2_eu_2021.geojson` (18 MB) |
| Lizenz | © EuroGeographics, Bedingungen siehe Eurostat Copyright Notice — frei nutzbar |
| Attribution | „© EuroGeographics for the administrative boundaries" |
| Verwendung | Punkt-in-Polygon-Lookup für `pesticides_data.py` |

### 6.2 Nominatim Geocoding (Adresse → lat/lon)

| Feld | Wert |
|---|---|
| **Status** | VERIFIZIERT, live |
| Quelle | OpenStreetMap Nominatim |
| Endpunkt | `https://nominatim.openstreetmap.org/` (öffentlicher Server) |
| Lizenz | ODbL 1.0 |
| Cache | Redis 30 Tage TTL — Nominatim-ToS empfehlen explizit Long-Term-Caching |
| Modul | `backend/app/geocode_cache.py` |
| Coverage | `countrycodes: "de,nl,at,ch"` |

---

## 7. Modell-Schätzungen (kein Messwert!)

Diese Werte sind **abgeleitete Schätzungen**, keine Messdaten. Der Report
muss jeweils den Schätz-Charakter explizit ausweisen.

### 7.1 RUSLE Erosion (Wassererosion)

| Feld | Wert |
|---|---|
| Modul | `backend/app/soil_directive.py:_estimate_erosion_rusle` |
| Formel | A = R × K × LS × C × P (t/ha/Jahr) |
| Quelle Modell | Wischmeier & Smith 1978; Panagos et al. 2015 (EU R-Faktor) |
| R-Faktor | aus `rfactor_data.py` — primär ESDAC-Raster (geplant), Fallback lat-linear für DE |
| K-Faktor | aus USDA-Texturklasse, Wischmeier-Tabelle |
| LS-Faktor | aus Slope (vereinfachte McCool-Formel) |
| C-Faktor | aus CORINE Land Cover (Panagos 2015 Tabelle) |
| P-Faktor | konstant 1,0 (keine Bodenschutz-Maßnahmen angenommen) |
| Schwelle | 2,0 t/ha/yr (Tolerable Soil Loss laut ESDAC) |
| Caveat im Report | „Modellschätzung nach RUSLE; tatsächliche Bodenabtragsmessung erfordert Probenahme" |

### 7.2 R-Faktor (Niederschlags-Erosivität)

| Feld | Wert |
|---|---|
| Modul | `backend/app/rfactor_data.py` |
| **Primärquelle (live seit 2026-05-01)** | ESDAC Panagos 2015, 1 km Raster, EPSG:3035 — `Rf_gp1.tif` aus dem ESDAC-Download `R_factorEU.zip` |
| Pixelpfad F: | `esdac_rfactor_eu_1km.tif` (449 MB) |
| Fallback (live), DE | `R = 150 - (lat - 47) × 14,3`, geclamped [30, 200] |
| Fallback (live), NL | Konstante 65 (Tiefland-Mittelwert) |
| Fallback (live), AT | Konstante 100 (Alpenanteil) |
| Fallback (live), CH | Konstante 150 (Alpenraum) |
| Andere Länder | Konstante 80 (generisch) |
| Source-Flag im Report | `r_source: "esdac-2015"` oder `r_source: "lat-linear-approx"` mit Note |
| Caveat | Solange ESDAC-Raster fehlt, ist der Wert eine Land-spezifische Konstante/Approximation und im Datenstrom als solche markiert |

### 7.3 N-Surplus (Stickstoff-Indikator)

| Feld | Wert |
|---|---|
| Modul | `backend/app/soil_directive.py` Part B |
| Formel | `surplus_kg_N_ha_yr ≈ N_total_mg_kg / 70` |
| Charakter | grobe Faustformel, **kein direkter Surplus-Messwert** |
| Schwelle | < 50 kg N/ha/yr (ok), 50–80 (warn), > 80 (alert) |
| Caveat im Report | „LUCAS-Indikator (kein direkter Surplus-Messwert)" — wörtlich |

### 7.4 EC / Salinisierung

| Feld | Wert |
|---|---|
| Modul | `backend/app/soil_directive.py` Part B |
| Charakter | regionale Approximation, **kein Messwert** |
| Defaults | Inland 0,15 dS/m; Küsten-sandig 0,8; Ton > 35 % → 0,3 |
| Schwelle | < 2,0 dS/m (gesund) |
| Caveat im Report | „Regional-Schätzung (kein direkter EC-Messwert)" — wörtlich |

### 7.5 WRB → AWC-Lookup

| Feld | Wert |
|---|---|
| Modul | `backend/app/soil_data.py:WRB_AWC_LOOKUP` |
| Eingabe | WRB-Klasse 1–29 (aus `soilhydro_awc_0-30cm.tif`, mis-benannt — enthält WRB-Codes, nicht direkte AWC-Werte) |
| Ausgabe | typische Available Water Capacity in mm/m |
| Quelle | WRB 2015 Reference Soil Group + ISRIC-Wasserretentions-Studien |
| Charakter | Lookup-Tabelle, **keine direkte AWC-Messung** |
| Caveat im Report | „WRB-basierte Schätzung (SoilGrids)" — wörtlich |

### 7.6 Wind-Erosionsrisiko

| Feld | Wert |
|---|---|
| Modul | `backend/app/soil_directive.py` Part A |
| Trigger | Sand > 60 % UND lat > 52 ° UND slope < 3 ° |
| Charakter | qualitatives Modell, kein Messwert |
| Caveat im Report | „Modellbasiert" oder „Für Standort nicht relevant" — wörtlich |

---

## 8. Honest Gaps — explizit als „nicht remote bestimmbar"

Diese 4 von 16 EU-Soil-Directive-Descriptoren werden im Report explizit
als `not_remote` ausgewiesen — keine Approximation, keine Schätzung,
sondern ehrlich „dafür braucht es eine Bodenprobe":

| Descriptor | Begründung im Report |
|---|---|
| Soil Biodiversity (Basalatmung) | „erfordert In-situ-Beprobung und Laborinkubation" |
| Microbial Diversity (eDNA) | „eDNA-Analyse erforderlich; ohne Bewertungskriterium" |
| PFAS | „In-situ-Beprobung nach DIN EN ISO 21675; EU-Liste Mitte 2027" |
| PAK / PCB | „Beprobung gemäß BBodSchV §8 Anhang 1 erforderlich" |

Pestizide sind **nicht** in dieser Liste, sondern werden via LUCAS NUTS2
abgedeckt (siehe §2.3).

---

## 9. Disziplin-Regel für künftige Layer

Bevor ein neuer Layer in einen Report eingebaut wird, **muss** er:

1. In diesem Doc als VERIFIZIERT, TEILWEISE oder GEPLANT eingetragen sein
2. Eine eindeutige Lizenz mit Attribution-Wortlaut führen
3. Einen dokumentierten Fallback haben (oder „nicht verfügbar" anzeigen,
   nie ein Standardwert ohne Hinweis)
4. Im Report-Output ein `source`-Feld führen, das im PDF zitiert wird

Modell-Schätzungen sind erlaubt, müssen aber **immer** als solche im
Report-Text und im Datenstrom (`r_source`, `*_source`-Felder) auftauchen.
Niemals einen Schätzwert ohne Schätz-Etikett rausgeben.

---

## 10. `data_provenance` — additives Honesty-Layer-Feld (V.0.6, Mai 2026)

Jedes Pipeline-Output-Modul ergänzt — **additiv**, keine bestehenden
Felder verändert — ein `data_provenance`-Dict pro relevantem Wert.
Die Visuals-Templates können daraus ehrliche Quell-Annotationen rendern
statt nackte Zahlen ("502 MJ·mm/(ha·h·yr) — ESDAC 1 km" statt "502").

### 10.1 Format

```json
{
  "data_provenance": {
    "source": "ESDAC Panagos 2015",
    "resolution_m": 1000,
    "sample_count": 1,
    "method": "Single-Pixel-Lookup im 1 km-Raster",
    "nearest_distance_m": null,
    "regional_scope": null
  }
}
```

| Feld | Pflicht | Typ | Beispiel | Beschreibung |
|---|---|---|---|---|
| `source` | ja | string | `"SoilGrids 250m"` | Datenquelle als Klartext-String. |
| `resolution_m` | ja | int \| null | `250` | Räumliche Auflösung in Metern. `null` wenn nicht-räumlich (z.B. Konstantnäherung). |
| `sample_count` | ja | int | `1`, `9`, `47` | Anzahl Datenpunkte, die in den Wert eingingen. `0` bei Konstantnäherung ohne echten Datenpunkt. |
| `method` | ja | string | `"IDW über 3 Nachbarn"`, `"Window-Mean 100 m"`, `"Multi-Scale-Steepest"` | Aggregations-/Lookup-Methode. |
| `nearest_distance_m` | optional | int \| null | `87` | Distanz zum nächsten echten Datenpunkt (z.B. LUCAS-Punkt) in Metern. |
| `regional_scope` | optional | string \| null | `"NUTS2 DE12"`, `"DE"` | Wenn der Wert nicht punktgenau, sondern auf Region aggregiert ist. |

### 10.2 Disziplin

- `method` darf **nur** beschreiben, was wirklich berechnet wurde. Kein
  `"Pearson r EGMS x DWD"` wenn die Pearson-Berechnung nicht stattgefunden
  hat. Kein `"IDW"` wenn nur ein Pixel-Lookup passiert ist.
- Wenn ein Wert komplett fehlt (z.B. NL-Adresse für DE-only Modul):
  `data_provenance` entfällt — Feld wird nicht gesetzt. Die Tatsache
  des Fehlens ist im `available: false`-Flag dokumentiert.
- Die Visuals-Templates müssen `data_provenance` als optional behandeln —
  ältere Module ohne den Block bleiben funktional.

### 10.3 Rollout-Stand 2026-05-01 (V.0.6)

| Modul | Stand |
|---|---|
| `geology.py` | ✓ produziert `data_provenance` ab Tag 1 |
| `building_footprint.py` | ✓ produziert `data_provenance` ab Tag 1 |
| `rfactor_data.py` | ✓ ergänzt 2026-05-01 |
| `slope_data.py` | ✓ ergänzt 2026-05-01 |
| `soil_data.py` (SoilGrids/LUCAS/CORINE/HRL/WRB) | offen — Sub-Sprint, nicht critical-path für V.1 |
| `pesticides_data.py` | offen — Sub-Sprint |
| `soil_directive.py` | offen — propagiert die Provenance der Sub-Module mit, sobald diese sie liefern |
| `kostra_data.py` | offen |
| `flood_data.py` | offen |
| `altlasten_data.py` | offen |
| `mining_nrw.py` | offen |

Folge-Tickets: pro Modul ein additives PR. Kein Modul muss "alle auf
einmal" durchziehen — die Visuals rendern auch mit teilweiser
Abdeckung, sie zeigen für Module ohne `data_provenance` den nackten
Wert ohne Quell-Annotation.

---

## 11. Visuals-Sprint-Module (Mai 2026)

V.0.1 bis V.0.6 + V.2/V.3 fügten neue Datenquellen ein, die explizit
für die sechs Visualisierungen entworfen wurden:

| Modul | Datenquelle | Status | Lizenz |
|---|---|---|---|
| `burland_classifier.py` | Burland 1995 (Settlement classification) | VERIFIZIERT | Pure Python, keine externe Lizenz |
| `correlations.py` | Pearson-Korrelation, eigene Berechnung über EGMS+DWD | VERIFIZIERT | n/a |
| `geology.py` | BGR GÜK250 ArcGIS REST identify | VERIFIZIERT | BGR Service-Lizenz |
| `building_footprint.py` | OpenStreetMap Overpass API | VERIFIZIERT | ODbL |
| `visual_payload.py` | Aggregator (kein eigener Datensatz) | VERIFIZIERT | n/a |
| `basemap.py` | CartoDB Positron (light_all) | VERIFIZIERT | CC BY 3.0 — Attribution: „© OpenStreetMap contributors © CARTO" |

Pflicht-Attribution für alle Reports und Landing-Embeds, die ein
Karten-Visual zeigen: **„© OpenStreetMap contributors © CARTO"** im
Footer der Karte (V.2.4-Template setzt das automatisch ab `basemap`-
Result mit `attribution`-Feld).

