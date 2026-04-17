# Phase 1 — Verifizierte Datenquellen für DACH-Groundsure-Parität

**Stand:** April 2026, URLs stichprobenhaft verifiziert via WebSearch.
**Zweck:** Entscheidungsgrundlage für konkrete Phase-1-Integration. Alle URLs
vor der tatsächlichen Implementierung ein letztes Mal per `curl` oder Browser
prüfen — Behörden-Endpoints ändern sich selten, aber es passiert.

---

## 0. Ist-Stand — was wir wirklich haben

### 0.1 Rasterdaten auf `F:\jarvis-eye-data\geoforensic-rasters\` (total ~130 MB)

| Datei | Quelle | Status im Report |
|---|---|---|
| `soilgrids_{bdod,clay,phh2o,sand,silt,soc}_0-30cm.tif` (DE) | ISRIC | ✅ integriert |
| `soilgrids_*_0-30cm_nlde.tif` (DE+NL kombiniert) | ISRIC | ✅ integriert (`soil_data.py`) |
| `corine_2024_100m.tif` | Copernicus CLMS | ⚠️ importiert, **Klassifikation in `soil_data.py` vordefiniert, aber im Report nicht gerendert**. **Achtung:** Laut Copernicus ist CLC2024 erst **Mitte 2026** regulär verfügbar — Datei-Name eventuell irreführend. Vermutlich CLC2018. **Vor Integration verifizieren.** |
| `hrl_imperviousness_20m.tif` | Copernicus CLMS (High-Resolution Layer) | ⚠️ importiert, nicht im Report genutzt |
| `soilhydro_awc_0-30cm.tif` | ESDAC | ⚠️ importiert, nicht im Report genutzt |
| `lucas_soil_de.csv` | JRC | ✅ integriert (Schwermetalle + Nährstoffe) |
| `lucas_pesticides_nuts2.xlsx` | JRC ESDAC | ⚠️ importiert, nicht im Report |

### 0.2 EGMS auf `F:\geoforensic-data\egms\`

- DE: **16 GB** (7.9M Punkte laut letztem Import-Lauf in PostGIS auf Contabo)
- NL: **1.2 GB** (3.25M Punkte, Import-Status Server unklar — muss verifiziert werden)

### 0.3 Zusammenfassung

**Wir haben bereits auf der Platte** (nur Integration fehlt):
1. CORINE Land Cover → Landnutzungs-Risikoflags
2. HRL Imperviousness → Versiegelungsgrad
3. LUCAS Pestizide → regionale Pestizid-Indikatoren (NUTS2)
4. SoilHydro AWC → Feldkapazität / Wasserspeicher

**Das sind 4 Quick Wins** à 4-6 Stunden Integration. Sollten **vor** neuen
externen Datenquellen gehoben werden, weil die Daten schon auf unserer
Infrastruktur liegen.

---

## 1. Bestehende Assets aktivieren (1-2 Tage Gesamtaufwand)

| # | Layer | Report-Wirkung | Aufwand |
|---|---|---|---|
| 1.1 | **CORINE Land Cover** — Risikoflags (121=Industrie, 122=Straße/Bahn, 131=Abbauflächen, 133=Baustellen) auslesen | Indikator "Standort liegt in ehemaliger Industriezone" | 4-6 h |
| 1.2 | **HRL Imperviousness** — Versiegelungsgrad in % am Standort | Indikator "dicht bebaut" / "naturnah" | 4 h |
| 1.3 | **LUCAS Pestizide** — Excel → Postgres + NUTS2-Zuordnung | Abschnitt "Regionale Pestizid-Belastung" | 4-6 h |
| 1.4 | **SoilHydro AWC** — Wasserspeicher in mm | Ergänzung Abschnitt "Bodenqualität" | 2 h |

---

## 2. Hochwasser (EU-HWRM) — einfach, kostenlos, DE-weit

**Quelle:** BfG Geoportal (zentraler Einstieg) + Länder-WMS (Details).

| Detail | Wert |
|---|---|
| URL (Portal) | `https://geoportal.bafg.de/karten/HWRM_2026/` |
| Update | Zyklus 3 der HWRM-RL: Karten aktualisiert **bis Dez 2025**, veröffentlicht **Mitte Januar 2026** |
| Abdeckung | DE-weit, 3 Szenarien (häufig HQ10, mittel HQ100, extrem HQ_extrem) |
| Lizenz | Meist dl-de/by-2.0 (kommerziell OK mit Attribution) — pro BL prüfen |
| Format | WMS + WFS |
| Aufwand | **3-5 Tage** (BfG als Basis + Query-Integration) |

**Länder-WMS als Referenz** (tiefer, für Premium-Deep-Dive):
- NRW: `https://www.wms.nrw.de/` → HWRM-RL Risiko- und Gefahrenkarte
- MV: LUNG Geoportal
- BW: `hochwasser.baden-wuerttemberg.de`
- Bayern: IÜG Bayern LfU

**Impact:** Sehr hoch. Hochwasser ist das #1 Thema in Klimawandel-Diskussion,
für Käufer direkt finanziell relevant (Versicherungsprämien, Elementarschaden).

---

## 3. Radon (BfS) — einfach, kostenlos, DE-weit

**Quelle:** BfS Geoportal mit direktem WMS-Endpoint.

| Detail | Wert |
|---|---|
| WMS GetCapabilities | `https://www.imis.bfs.de/cgi-public/wms_geoportal?REQUEST=GetCapabilities&SERVICE=WMS&VERSION=1.3.0` |
| Geoportal (interaktiv) | `https://www.imis.bfs.de/geoportal/` |
| Radon-Vorsorgegebiete-Übersicht | `https://www.bfs.de/DE/themen/ion/umwelt/radon/karten/vorsorgegebiete.html` |
| Radon in Bodenluft | `https://www.bfs.de/DE/themen/ion/umwelt/radon/karten/boden.html` |
| Abdeckung | DE-weit, Gemeinde-Ebene |
| Lizenz | Frei (CC BY meist) |
| Format | WMS + Shapefile-Download von Listen |
| Aufwand | **2-3 Tage** |

**Zwei Werte relevant:**
1. **Radon-Vorsorgegebiete** (Stand 15. Juni 2021, rechtlich verbindlich nach §121 StrlSchG): kategorisch pro Gemeinde
2. **Radon-Konzentration in Bodenluft** (Raster, diffuser)

**Impact:** Hoch. Rechtlich seit 2021 relevant (StrlSchG Paragraph 121+153),
Käufer googeln's aktiv, **DE-weit kein Konkurrent hat das integriert** für
den €-Preispunkt.

---

## 4. Erdbebenzonen (BGR + GFZ) — mittel wichtig

**Quelle:** BGR + DFG-Abfragetool der Gesellschaft für Erdbebenzonenabfrage.

| Detail | Wert |
|---|---|
| BGR Erdbebendienst | `https://www.bgr.bund.de/DE/Themen/Kernwaffenteststopp-Geogefahren/Erdbebendienst_Bund/` |
| DIN EN 1998-1/NA Abfrage (GFZ) | `https://www.gfz.de/en/din4149-erdbebenzonenabfrage` |
| Standard | DIN EN 1998-1/NA:2011-01 (4 Zonen 0-3) — Nachfolger E DIN EN 1998-1/NA:2018-10 (kontinuierlich) |
| Abdeckung | DE-weit |
| Lizenz | BGR-Lizenz — **kommerzielle Nutzung bitte vor Integration bei BGR anfragen** |
| Format | WMS verfügbar, konkreter Endpoint bei BGR anzufragen |
| Aufwand | **3-5 Tage** + Lizenz-Klärung (1-2 Wochen) |

**Relevanz:** Nur Südwest-DE wirklich betroffen (Rheingraben, Schwäbische Alb,
Niederrheinische Bucht, Vogtland). Für restliche 80% der DE-Adressen zeigt
der Layer "Zone 0" = unauffällig.

**Empfehlung:** Eher **Phase 2** — aufwändig relativ zum Impact für den
durchschnittlichen Käufer.

---

## 5. Bodenrichtwerte (BORIS-D) — Markt-Kontext

**Quelle:** BORIS-D Bundesportal + Länder-Portale (heterogen).

| Detail | Wert |
|---|---|
| Bundesportal | `https://www.bodenrichtwerte-boris.de/` |
| NRW | Open Data, **WFS + WCS**, Lizenz `dl-de/zero-2.0` (keine Restriktionen, kommerziell voll OK) |
| Brandenburg | Neue WMS/WFS seit Jan 2025 |
| Hessen | WFS mit AdV-Extensions |
| Bayern | BORIS-Bayern, eigenes Portal |
| Abdeckung | **Nicht alle BL angeschlossen** — je nach BL unterschiedlich detailliert |
| Update-Rhythmus | Stichtag 01.01. jährlich, Veröffentlichung meist März-Juni |
| Aufwand | **1-2 Wochen** (heterogene Länder-APIs) |

**Wichtig:** NRW hat `dl-de/zero-2.0` = die kommerziell-freundlichste Open-Data-
Lizenz überhaupt. **Für NRW ist BORIS ein No-Brainer.**

**Impact:** Medium. Käufer kennen Preise meist durch Makler. Aber: gibt dem
Report Markt-Kontext und wirkt professionell ("Standort liegt 12% unter
Gemeinde-Durchschnitt").

---

## 6. Bergbau (NRW als Basis) — regional hoch relevant

**NRW ist Vorreiter:** BergbauBerechtigungen sind **Open Data seit 2024**.

| Detail | Wert |
|---|---|
| WMS Bergbauberechtigungen NRW | `https://www.wms.nrw.de/` → Dienst "Bergbauberechtigungen" |
| BAV-Kat (Bergbau Alt- und Verdachtsflächen) | Bezirksregierung Arnsberg, Atom-Feed für Download, Shapefile-Format |
| GDU (Gefährdungspotenziale des Untergrundes) | Geologischer Dienst NRW: `https://www.gd.nrw.de/gg_oa.htm` |
| Saarland | BAS Saar-Kataster, WMS teilweise, teils Behördenauskunft |
| Sachsen-Anhalt | LAGB Halle, WMS verfügbar |
| Lizenz | dl-de (NRW voll Open Data) |
| Aufwand NRW | **1 Woche** |
| Aufwand Saar + S-A dazu | +1 Woche |

**Impact:** Sehr hoch für Ruhrgebiet, Saarland, Leipzig-Halle. Für Berlin oder
München nahezu irrelevant. **Regional-selektiv sinnvoll.**

---

## 7. Altlasten-Kataster (pro Bundesland) — schwierig, aber wertvoll

**Realität:** Föderales Chaos. Kein zentraler Zugriff, jede BL eigenes System,
oft nur Einzelauskunft auf Antrag.

### Top-5-BL (deckt ~65 % DE-Bevölkerung)

| BL | System | Status |
|---|---|---|
| **NRW** (LANUV FIS AlBo) | **Unvollständig** — 87.892 gemeldete Flächen (33k Abfall, 55k Gewerbe; Stand Juni 2023). LANUK gesetzlich verpflichtet nach §9 LBodSchG NRW. **Kein offenes WMS**, Auskunft via ELWAS-WEB möglich (Einzelabfrage). | ⚠️ schwer |
| **Bayern** (LfU BIS / ABuDIS 3.0) | Öffentlich zugänglich, **aber personenbezogene Daten (Flurstücke, Adressen) aus Datenschutzgründen nicht enthalten** — Einzelauskunft über Landratsamt | ⚠️ Verdachtsflächen-Karte ja, Details behördenpflichtig |
| **BW** (LUBW UDO) | Öffentlich: UDO Portal, interaktive Karte + Metadaten-Service (RIPS) | ✅ Zugriff möglich |
| **Niedersachsen** (NIBIS) | Kartenserver `https://nibis.lbeg.de/cardomap3/`, WMS verfügbar | ✅ |
| **Berlin** (FIS-Broker) | `https://fbinter.stadt-berlin.de/fb/` — Open Data | ✅ voll offen |

### Realistische Strategie

- **Kurzfristig (Phase 1a):** Bayern + BW + Berlin integrieren. NRW + NI
  in Phase 1b wenn LANUV-Zugang klar ist.
- **Pragmatischer Alternative:** Statt eigenes Kataster nur **Link zum
  BL-Portal** im Report platzieren ("Altlasten-Auskunft für Ihren Standort:
  [BL-spezifische URL]"). Keine eigene Integration nötig, User macht selber.
  **Kostet 2 Stunden statt 5 Wochen.**

**Aufwand vollintegriert:** 3-5 Wochen für Top-5-BL.
**Aufwand "nur verlinken":** 4 Stunden.

**Empfehlung:** Starten mit "nur verlinken", später bei Bedarf nachtiefen.

---

## 8. Historische Nutzung / TK25 historisch — visuell wirkungsvoll

**Zweck:** Altlasten-Indikator. Wenn Standort 1960 noch Kohle-Hochofen war,
höheres Kontaminations-Risiko.

| Detail | Wert |
|---|---|
| BKG Geodatenzentrum | `https://gdz.bkg.bund.de/` |
| WMS DTK25 (aktuell) | `https://gdz.bkg.bund.de/index.php/default/wms-digitale-topographische-karte-1-25-000-wms-dtk25.html` |
| Historische Zeitschnitte | **Nur einzelne BL** (Hessen hat 1900/1945/1970/1990, andere heterogen) |
| BayernAtlas Historische Karte | Bayern LDBV, frei verfügbar |
| Lizenz | DTK25 aktuell: **Open Data**. Historische: je BL unterschiedlich, teils kostenpflichtig |
| Aufwand | **2-3 Wochen** — heterogene Länder-Quellen |

**Empfehlung:** **Phase 2** — aufwendig und visuell, aber automatisierte
Interpretation ist schwierig. Eher als "Karten-Thumbnail im Report" mit
manuellem User-Interpretations-Hinweis.

---

## Realistische Phase-1-Reihenfolge

Wenn ich das eine Dev-Monat planen müsste, wäre das die Reihenfolge nach
**Impact pro Stunde Aufwand**:

### Woche 1 — Low-hanging fruit (5-6 Tage total)
1. LUCAS Pestizide integrieren (haben wir, 6h)
2. CORINE Land Cover Risikoflags im Report anzeigen (6h)
3. HRL Imperviousness als Zusatzmetrik (4h)
4. SoilHydro AWC im Bodenqualitäts-Abschnitt (2h)

→ **Sichtbarer Report-Fortschritt, keine externen Abhängigkeiten**

### Woche 2-3 — Externe Quick Wins (8-10 Tage)
5. **Radon (BfS)** — WMS einbinden, Vorsorgegebiete-Layer (3 Tage)
6. **Hochwasser (BfG HWRM)** — 3 Szenarien (HQ10, HQ100, HQ_extrem), nationales WMS (5 Tage)

→ **Hier kommt der "Aha-Effekt" für Käufer: Hochwasser-Risiko und
gesundheitsrelevantes Radon**

### Woche 4 — Markt & NRW-Bonus (5 Tage)
7. **BORIS-D** — mindestens NRW-Integration (dl-de/zero, am einfachsten)
8. **NRW Bergbau** (Open Data) — ergänzt Datentiefe fürs Ruhrgebiet

→ **Marktwerts-Kontext + regional differenzierte Aussagen**

### Parkplatz (Phase 2)
- Altlasten-Kataster (erst "Verlinken", später integrieren)
- Erdbebenzonen BGR (Lizenz-Abklärung nötig)
- Historische Karten (aufwendig, mittelmäßiger Impact)
- Saarland + Sachsen-Anhalt Bergbau

---

## Licensing-Übersicht (nur verifizierte Quellen)

| Quelle | Lizenz | Kommerziell OK? |
|---|---|---|
| Copernicus EGMS | CC BY 4.0 | ✅ mit Attribution |
| ISRIC SoilGrids | CC BY 4.0 | ✅ |
| JRC LUCAS | CC BY 4.0 | ✅ |
| JRC ESDAC Pestizide | Creative Commons (Details pro Dataset) | ⚠️ pro Dataset prüfen |
| Copernicus CORINE/HRL | Kommerziell OK | ✅ |
| BfS Radon | meist CC BY | ✅ |
| BfG HWRM | dl-de/by-2.0 | ✅ |
| BORIS NRW | **dl-de/zero-2.0** | ✅ voll ohne Restriktionen |
| BORIS andere BL | heterogen | ⚠️ pro BL prüfen |
| BGR Erdbeben | BGR-Lizenz | ⚠️ Nachfrage nötig für kommerzielle Nutzung |
| LANUV NRW Altlasten | dl-de meist | ✅ (wenn Zugriff möglich) |
| BKG DTK25 | Open Data | ✅ |
| BKG TK25 historisch | heterogen | ⚠️ |

---

## Offene Fragen vor Implementation

1. **CORINE-Datei-Name:** Ist `corine_2024_100m.tif` wirklich CLC2024 oder
   fehlerhaft benannter CLC2018? (CLC2024 offiziell erst Mitte 2026 verfügbar)
2. **EGMS NL auf Server:** Ist der Import auf Contabo wirklich durchgelaufen
   oder nur die 16 GB DE? → `docker compose exec db psql -c "SELECT country,
   COUNT(*) FROM egms_points GROUP BY country;"`
3. **BGR-Lizenz:** Antwortet BGR auf die E-Mail zur kommerziellen Nutzung?
   (Memory sagt E-Mail an `BBD@bgr.de` nie beantwortet)
4. **Altlasten-Strategie:** Vollintegration (5-8 Wochen) oder
   "Verlinken-Only" (4 Stunden)?
5. **Zusatzlayer Imperviousness (HRL 20m) & CORINE Risikoflags im Free-Report
   oder Premium-only?** → Wahrscheinlich Premium, sonst wird der Free zu dicht
   und wir haben keinen Trennungsgrund mehr.

---

## Commit-Strategie für die Implementierung

Jede der 8 Phase-1-Aufgaben ein **eigener Feature-Branch** + eigener Commit.
Nicht alles in einem Wash, weil:
- Wenn eine Quelle offline ist, bricht sonst alles
- Rollback pro Quelle möglich
- Review einfacher

**Branch-Naming:** `feat/phase1-corine`, `feat/phase1-pesticides`,
`feat/phase1-radon-bfs`, `feat/phase1-hochwasser-bfg` etc.
