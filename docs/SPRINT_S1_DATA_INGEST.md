# SPRINT_S1_DATA_INGEST.md — Datenquellen + Server-Upload-Pfad

**Stand:** 2026-04-27, **mehrfach revidiert nach Live-Verifizierung**.
Begleitet die Strategie aus
[`MARKET_REALITY_DE_2026.md`](MARKET_REALITY_DE_2026.md) (Option B —
Soil-Act + InSAR + eigene Modelle aus Roh-Quellen).

**Verifizierungs-Doc:** Der einzige Layer-Katalog dem wir vertrauen
ist [`DATA_SOURCES_VERIFIED.md`](DATA_SOURCES_VERIFIED.md). Bei jeder
Diskrepanz zwischen diesem Doc und dem Verifizierungs-Doc gilt das
Verifizierungs-Doc.

**Korrekturen gegenüber früheren Versionen:**
- BBSR GIS-ImmoRisk: blockiert (Lizenz nicht deklariert, kein
  Maschinen-Zugang). Mail an `zentrale@bbr.bund.de` ausstehend.
- Erdbebenzonen DIN EN 1998-1/NA: Quelle ist **GFZ Potsdam**, nicht
  BGR. Frühere Annahme war falsch.
- BfS Radon: kein einheitlicher WMS — 5 Landes-Verordnungen
  einzeln zu pflegen. Kein Quick-Win.
- DWD KOSTRA: kein WMS, nur Raster-Download. Pattern A statt C.
- BfG HWRM: Lizenz nur Sekundärquelle bestätigt, Capabilities-Live-Test
  ausstehend (Cloud-Sandbox blockt, vom VPS testen).

---

## 1. Server-Upload-Pfad (heute schon etabliert)

Aus `DEPLOYMENT.md` + `docker-compose.yml` verifiziert. Drei Patterns
sind im Repo etabliert; neue Layer sollten in eines davon passen.

### Pattern A — Raster-Datei (GeoTIFF)

Beispiel: SoilGrids, CORINE.

```
[lokaler PC]                   [VPS]                          [Container]
F:\geoforensic-rasters\*.tif → /opt/bodenbericht/rasters/  → /app/rasters (ro mount)
                       (scp -r)                       (docker-compose volume)
```

Ablauf:
```bash
# 1. Vom lokalen PC
scp -r FILE.tif root@185.218.124.158:/opt/bodenbericht/rasters/

# 2. Auf dem VPS — Backend muss neu starten, damit SoilDataLoader die
#    neue Datei einliest (Loader cached den Dateibestand beim Boot)
ssh root@185.218.124.158
cd /opt/bodenbericht
docker compose restart backend
```

Code-seitig: neuen Eintrag in `backend/app/soil_data.py` ergänzen
(siehe `SOILGRIDS_PROPERTIES`-Dict als Vorbild) und in
`generate_full_report` integrieren.

### Pattern B — Tabular (CSV/Parquet → PostGIS)

Beispiel: EGMS-Punkte, LUCAS-Schwermetalle.

```
[lokaler PC]                  [VPS]                          [PostGIS]
egms_de.parquet         →   /opt/bodenbericht/imports/   →  egms_points (Tabelle)
                       (scp)                  (Import-Script im Container)
```

Ablauf:
```bash
# 1. Vom lokalen PC
scp egms_de.parquet root@185.218.124.158:/opt/bodenbericht/imports/

# 2. Auf dem VPS — Import-Script im laufenden Container
ssh root@185.218.124.158
cd /opt/bodenbericht
docker compose exec backend \
  python -m scripts.import_egms_parquet \
  --parquet /app/imports/egms_de.parquet --country DE
```

Vorlagen: `backend/scripts/import_egms_*.py`. Für eine neue Tabelle
brauchen wir zusätzlich eine **Alembic-Migration** unter
`backend/alembic/versions/`, damit das Schema versioniert ist.

### Pattern C — WMS/WFS-live (kein Upload)

Beispiel: Nominatim/OSM für Geocoding heute. Kein Datenupload, das
Backend ruft den Behörden-WMS bei Bedarf auf.

Vorteile: keine Datenpflege, keine Lizenz-Komplexität durch lokale
Kopien. Nachteile: Latenz pro Report, Abhängigkeit von Behörden-Uptime,
typischerweise rate-limitiert.

Code-seitig: neue Funktion analog `fetch_static_map`, mit
`httpx.AsyncClient` und Timeout. Für GetFeatureInfo-Calls (Punkt im
Polygon abfragen) ist `requests` mit XML-Parser ausreichend.

**Empfehlung neuer Layer:** WMS-live als Default. Erst auf Pattern A/B
wechseln, wenn das WMS spürbar zu langsam wird oder bei Ausfällen
keine sinnvolle Fallback-Antwort liefert.

---

## 2. Layer-Plan (priorisiert)

### S1 — sofort umsetzbar

#### Hochwasser (BfG) — grünstes Licht

| Quelle | URL | Format | Lizenz | Aufwand |
|---|---|---|---|---|
| BfG Geoportal HWRM 2025 | `https://geoportal.bafg.de/karten/HWRM_Aktuell/` | WMS | **GeoNutzV — kommerziell OK** | 1–2 Tage |

- Kommerziell explizit erlaubt, INSPIRE-konform, Quellenangabe
  „© BfG, GeoNutzV" Pflicht
- Polygone für HQ10/HQ100/HQextrem, Punkt-im-Polygon-Abfrage pro
  Adresse
- Pattern C (WMS-live) — kein Upload, nur Code

**Implementierungsskizze:**
- Neue Funktion `query_flood_zone(lat, lon)` in z. B.
  `backend/app/flood_data.py`, ruft BfG-WMS GetFeatureInfo auf
- Aufruf aus `_generate_and_send_lead_report` für den Full-Pfad
- Neuer Abschnitt in `full_report.py` zwischen „Bodenbewegung" und
  „Schwermetallen"

#### Radon (BfS) — Layer-Lizenz prüfen, sonst ähnlich

| Quelle | URL | Format | Lizenz | Aufwand |
|---|---|---|---|---|
| BfS Radon-Vorsorgegebiete | `https://www.bfs.de/DE/themen/ion/umwelt/radon/karten/vorsorgegebiete.html` | WMS / Download | **pro Layer prüfen** (BfS-Geoportal-Sitepolicy verlangt Einzelcheck) | 1 Tag (nach Lizenzklärung) |
| BfS Radon-Karte (Bodenluft) | `imis.bfs.de/geoportal` | WMS / Raster (10×10 km) | pro Layer prüfen | 0,5 Tag |

- Granularität: rechtsverbindliche Vorsorgegebiete sind auf
  **Gemeinde**-Ebene ausgewiesen (§121 StrlSchG), nicht parzellenscharf
- Aussage im Bericht ist „Gemeinde X ist Vorsorgegebiet ja/nein"
- Pattern C (WMS-live)
- TODO vor Integration: Metadaten-Eintrag pro Layer im BfS-Geoportal
  lesen, Lizenz dokumentieren

### S2/S3 — kann folgen

#### Erdbebenzonen (BGR / DIN EN 1998-1/NA)

| Quelle | URL | Format | Lizenz | Aufwand |
|---|---|---|---|---|
| BGR Erdbebenzonenkarte | (im BGR-Geoportal) | WMS | dl-de/by-2.0 (üblich, **verifizieren**) | 1 Tag |

- Rechtsverbindlich für Bauwerksauslegung — relevanter Käufer-Layer
  in RH-Pf, BW, Sachsen
- Ersetzt potenziell den BBSR-Erdbeben-Layer (BBSR nutzt KIT-Daten,
  BGR-Karten haben den DIN-Status)
- Pattern C (WMS-live)

#### Bergbau / Altbergbau

| BL | Quelle | Lizenz |
|---|---|---|
| NRW | Bezirksregierung Arnsberg WMS | dl-de/by-2.0 (üblich, verifizieren) |
| BW | LGRB Geoportal WMS | dl-de/by-2.0 |
| ST | LAGB — teils WMS, Detail nur per Anfrage | dl-de/by-2.0 vermutlich |
| SL | BAS — überwiegend Behördenanfrage | restriktiv |
| Ruhr | RAG-Stiftung Detail-Daten | **NICHT frei kommerziell — off-limits** |

- Regionaler Add-on-Layer; in nicht betroffenen BL einfach „nicht
  relevant für Ihren Standort" anzeigen
- Pattern C für die WMS-Layer; RAG-Stiftung gar nicht nutzen
- Aufwand: 2–3 Tage für die ersten 2 BL (NRW, BW)

#### DWD-Klimakarten (alternativ zu BBSR-Hitze/Starkregen)

Falls BBSR-Lizenz nicht kommt: direkter Bezug aus DWD-Klima-Daten
denkbar. **Im Detail noch nicht recherchiert** — gehört in einen
Folge-Sprint.

| Quelle | Format | Lizenz |
|---|---|---|
| DWD CDC OpenData | Download / WCS / WMS | GeoNutzV — kommerziell OK |

- KOSTRA-DWD für Starkregen-Wiederkehrintervalle
- Klimaprojektionen (Hitze) aus DWD-CDC

### S4+ — schwierig oder verschoben

#### Altlastenkataster

| BL | Status |
|---|---|
| NRW (LANUV) | kein public WMS, Anfrage über Untere Bodenschutzbehörde |
| BY (LfU) | WMS für Altablagerungen-Übersicht, Detail per Anfrage |
| BW (LUBW) | UDO-Portal teils Altlasten, Detail kreisbasiert |
| NI (LBEG NIBIS) | Altlasten-Übersicht WMS, **offenste der fünf** |
| HE (HLNUG ALTIS) | Auskunft kreisbasiert |

**docestate-Modell:** Behördenanfrage-as-a-Service mit menschlichem
Bearbeitungsschritt — kein automatisierter Datenlayer. Für ein
automatisiertes SaaS heißt das: Altlasten lassen sich kurzfristig nur
als „Hinweis-Layer" abbilden („in dieser Region existiert
Altlastenverdacht / nicht"), nicht parzellenscharf. **Verschoben** auf
nach Phase-1.

#### BBSR GIS-ImmoRisk Naturgefahren

**Blockiert.** Drei Probleme:

1. Lizenz nicht öffentlich deklariert (Drittdaten von GDV/Munich Re
   im Mix → keine Pauschalannahme dl-de/by-2.0)
2. Kein WMS/WFS/API — nur Web-Tool
3. Scraping rechtlich und technisch fragil

**Vorgehen:**
- Mail an `zentrale@bbr.bund.de` (Vorlage:
  [`MAIL_BBSR_LIZENZ.md`](MAIL_BBSR_LIZENZ.md))
- Bis Antwort: weder ingesten noch verlinken
- Falls Antwort negativ: alternativen Pfad über DWD/BGR-Quell-WMS
  gehen (mehr Aufwand, lizenzsauber)

---

## 3. Reihenfolge der Umsetzung — revidiert nach Verifizierung

Empfehlung für die nächsten 2–3 Sprints. Genaue Verifizierungs-Stati
in [`DATA_SOURCES_VERIFIED.md`](DATA_SOURCES_VERIFIED.md).

| Sprint | Inhalt | Status | Voraussetzung |
|---|---|---|---|
| S1 | NRW Bergbau-WMS — neues Modul + Bericht-Abschnitt | grünes Licht | keine, sofort starten |
| S1 | DWD KOSTRA Download-Pipeline + Raster-Hosting | Engineering startbar | vom VPS Index-File holen, ein Test-Raster ziehen |
| S2 | BfG HWRM-WMS — nach Live-Verify | bedingt | Capabilities + AccessConstraints vom VPS lesen |
| S3 | NL-i18n des Reports + KCAF/FunderMaps-Anbindung | offen | Pricing-Entscheidung |
| pending | BBSR GIS-ImmoRisk | Mail-Antwort abwarten | `zentrale@bbr.bund.de` |
| pending | GFZ Erdbebenzonen DIN EN 1998-1/NA | Quelle korrigiert, Lizenz-Klärung offen | Mail an GFZ |
| pending | BfS / Landes-Radon | Patchwork, Phase-2 | je BL Lizenz-Check |
| pending | Altlasten-Hinweislayer | Konzept docestate-Hybrid offen | unverändert |

**Wichtig:** Vor jeder Layer-Integration ein **Lizenz-Verify-Schritt** —
GetCapabilities-Call + Metadata-Eintrag im Geoportal lesen, Lizenz im
Code-Kommentar dokumentieren. Wir wollen nicht erneut auf einen
„dl-de/by-2.0 angenommen, war aber nicht"-Tritt wie bei BBSR laufen.

---

## 4. Caveats aus der Recherche

- **URLs nicht alle live verifiziert.** Die Recherche basierte auf
  Trainingsdaten + öffentlichen Sekundärquellen. Vor jeder Integration
  ein eigener Verifizierungs-Sprint nötig
  (`?SERVICE=WMS&REQUEST=GetCapabilities`).
- **Lizenztexte ändern sich.** Was 2024 als dl-de/by-2.0 ausgewiesen
  war, kann 2026 anders sein. Lizenz pro Layer im Code als Kommentar
  oder Konstante festhalten und bei jedem Layer-Update neu prüfen.
- **Granularität ≠ Pro-Adresse.** Mehrere Layer (Radon-Vorsorge,
  BBSR-Hitze) sind auf Gemeinde- oder Raster-Ebene aggregiert. Im
  Bericht muss das transparent kommuniziert werden („auf Gemeinde-Ebene
  klassifiziert"), sonst entsteht falsche Präzisionserwartung.
