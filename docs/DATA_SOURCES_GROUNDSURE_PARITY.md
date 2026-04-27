# Datenquellen-Roadmap — Groundsure-Parität für DACH

**Ziel:** Paid-Report (Cozy full) soll inhaltlich auf Augenhöhe mit Groundsure UK
operieren, angepasst an den DACH-Datenraum.

**Kontext:** Free-Landing bleibt bei EGMS + SoilGrids + LUCAS. Paid-Report bekommt
alle zusätzlichen Schichten, die Hauskäufer / Makler / Banken wirklich wollen.

---

## Was wir HEUTE haben (lokal auf F: / PostGIS)

| Datenquelle | Format | Coverage | Stand |
|---|---|---|---|
| Copernicus EGMS (L3 Ortho U) | PostGIS | DE 7.9M Punkte, NL 3.25M (ggf. nochmal importieren) | ✅ im Report |
| ISRIC SoilGrids 250m | GeoTIFF | global, 6 Layer (phh2o, soc, bdod, clay, sand, silt) | ✅ im Report |
| JRC LUCAS Topsoil | CSV → PostGIS | DE ~3000 Punkte, EU ~22k | ✅ im Report |
| ESDAC Pestizide (118 Substanzen, NUTS2) | Excel | EU | ❌ **noch nicht integriert** |
| Copernicus CORINE Land Cover | Raster | EU, 100m | ❌ importiert aber nicht interpretiert |
| Copernicus HRL (High-Res Layers) | Raster | EU, Imperviousness/Tree Cover etc. | ❌ importiert, Zweck klären |
| Nominatim / OSM | API | global | ✅ für Geocoding |

---

## Phase 1 — DACH-Pflicht (Top 8, sollte alles im Paid-Report landen)

### 1. Altlasten-Verdachtsflächen (BBodSchG)

**Warum Pflicht:** Der wichtigste Punkt beim Hauskauf. Auskunft nach §9 BBodSchG
ist landesrechtlich geregelt.

**Realität:** Pro Bundesland unterschiedliches System. Keine Bundes-API.

| BL | Quelle | Open Data? |
|---|---|---|
| NRW | Altlasten-Kataster (LANUV) | Teilweise, WMS |
| BW | FIS Boden (LUBW) | WMS ja, Details nur Behörde |
| Bayern | BIS (LfU) | Eingeschränkt |
| Niedersachsen | NIBIS (LBEG) | Teilweise WMS |
| Hessen | Altlastenkataster | Behördenanfrage |
| Sachsen | SALKA | WMS |
| Berlin | FIS-Broker | Open Data |
| Hamburg | Hamburg.de Bodenbelastung | Open Data |

**Aufwand:** 3-5 Wochen pro BL für Crawling/API-Anbindung; realistisch **nur
Top-5-BL in Phase 1** (NRW, BW, BY, NI, Berlin). Deckt ~65 % der Bevölkerung.

**Lizenz:** dl-de/by-2.0 meist, kommerziell nutzbar bei Attribution.

### 2. Hochwasser (EU-HWRM + Länder-ÜSG)

**EU-HWRM-Richtlinie 2007/60/EG** verpflichtet MS zu Hochwasserrisikokarten.
DE-Daten zentral bei BfG + verteilt bei Länder-Umweltämtern.

**Quellen:**
- BfG WMS (hochwasserzentrale.bund.de) — Flusshochwasser
- Länder-WMS für Überschwemmungsgebiete (ÜSG) — rechtlich verbindlich
- Starkregen/Sturzflut: Bayern **WADaBa**, NRW **KliMa-WMS**, andere BL im Aufbau
- Copernicus EMS Flood Mapping — historische Ereignisse

**Aufwand:** 1-2 Wochen für Basis (EU-HWRM + 3 größte BL ÜSG).
**Lizenz:** meist frei / dl-de.

### 3. Radon (BfS)

**Warum Pflicht:** Seit StrlSchG 2021 müssen Radon-Vorsorgegebiete ausgewiesen
werden. Arbeitgeber haben Messpflicht. B2C: Hauskäufer fragen explizit danach.

**Quelle:** BfS Radon-Potential-Karte (WMS), pro Gemeinde klassifiziert.
**Aufwand:** 2-3 Tage.
**Lizenz:** frei (CC BY).

### 4. Pestizide (ESDAC) — **nur Integration nötig**

**Quelle:** `F:\jarvis-eye-data\geoforensic-rasters\lucas_pesticides_nuts2.xlsx`
(118 Substanzen, NUTS2-Ebene)

**Caveat:** NUTS2 = Regionalebene (z.B. ganz Oberbayern = ein Wert). Sagt nichts
über einzelnes Grundstück, aber als "regionale Indikation" nutzbar.

**Aufwand:** 4-6 Stunden (Excel → PostgreSQL → report-Integration).

### 5. Erdbebenzonen + Tektonik

**Quellen:**
- BGR Erdbebenzonenkarte (DIN EN 1998-1/NA) — rechtsverbindlich für Bau
- BGR Geogene Gefährdungen (Tektonische Störungen)

**Aufwand:** 3-5 Tage.
**Lizenz:** BGR meist frei, kommerzielle Nutzung oft OK nach Attribution.

### 6. Bergbau-Risiko

**Warum relevant:** Ruhrgebiet, Saarland, Leipzig-Halle-Raum, Oberbayern
(Altbergbau). Einsturz-Risiken, Bergschäden-Ansprüche.

**Quellen pro BL:**
- NRW: **Bergbaukarte NRW** (LANUV / Bezirksregierung Arnsberg)
- Saarland: **BAS** (Bergbau-Altlasten Saar)
- BW: **LGRB** Altbergbau-Kataster
- Sachsen-Anhalt: **LAGB** Bergbauverbindlichkeitsgebiete
- RAG-Stiftung: historische Bergbau-Karten (Ruhrgebiet)

**Aufwand:** 2 Wochen für die 4 wichtigsten BL.
**Lizenz:** Großteil frei; manche Details kostenpflichtig.

### 7. BORIS Bodenrichtwerte

**Warum:** Gibt dem Report Markt-Kontext. "Standort liegt bei 850 €/m² —
Schnitt Gemeinde 720 €/m²".

**Quelle:** BORIS-D, pro BL separates Portal, teils WMS / WFS.
**Aufwand:** 1-2 Wochen, Länder-Mix.
**Lizenz:** meist frei, pro BL unterschiedlich.

### 8. Historische Nutzung (TK25 / TK50 historisch)

**Warum:** Altlasten-Indikator #1. Wer mal Tankstelle, Lackierei, Chemiewerk
war, hat höheres Risiko.

**Quellen:**
- BKG Topographische Karten TK25 ab ~1880 (historische Layer)
- BayernAtlas Historische Karte
- Landesvermessungsämter pro BL

**Aufwand:** 3 Wochen, aber visuell wirkungsvoll.
**Lizenz:** teils frei, teils €/km².

---

## Phase 2 — Advanced (sobald Phase 1 läuft)

| Quelle | Zweck | Aufwand |
|---|---|---|
| Trinkwasserschutzgebiete (Länder) | Bau-Restriktion, Wertfaktor | 1 W |
| Lärm (UBA Fluglärm, BMDV Strassenlärm) | Wohnqualität | 3 T |
| Denkmalschutz | Bau-Restriktion | 1 W |
| Klimaprognose (DWD KLIWA) | Zukunftsszenarien | 1 W |
| Hitzeinseln (Copernicus LST) | Klimafolgen Stadt | 3 T |
| Kampfmittelverdacht (Länder) | Bau-Relevanz | 2 W |
| BNetzA EMF (Sendemasten) | Wohnqualität | 2 T |
| Verkehrsanbindung (OSM + Routing) | Lagebewertung | 1 W |

---

## NL-Markt (hat eigene, oft bessere Quellen)

| Quelle | Zweck | Stand |
|---|---|---|
| BAG (Basisregistratie Adressen en Gebouwen) | Bauwerksregister | Top-Qualität, frei |
| bodemdalingskaart.nl (SkyGeo InSAR) | Alternative zu EGMS-NL | CC BY-SA (Copyleft-Risiko, ggf. nicht nutzen) |
| AHN (Actueel Hoogtebestand NL) | Höhenmodell, Überflutung | frei, sehr hochauflösend |
| PDOK Risicokaart | Zentrale Gefahrenkarte | frei |
| KCAF FunderMaps | A-E Fundament-Label | kostenpflichtig, könnte Konkurrenz sein |
| BODEMLOKET | Bodenkarte, Altlasten NL | frei |

**Priorität NL:** AHN + BAG + Risicokaart + EGMS-NL-Import verifizieren.
Rest erst wenn Markt validiert.

---

## Kosten-Realitätscheck

**Eine Faustregel:** 80 % der wichtigen deutschen Geodaten sind in irgendeiner
Form frei (WMS/WFS/Open Data). Die anderen 20 % sind entweder kostenpflichtig
pro Abfrage (ALKIS, kommerzielle Provider) oder nur per E-Mail-Antrag verfügbar.

**Was "frei" bedeutet:**
- Meist dl-de/by-2.0 oder CC BY 4.0 → kommerzielle Nutzung mit Attribution OK
- Manche Layer: CC BY-SA → **Vorsicht**, erzwingt SA-Lizenz für abgeleitete Reports
- Attribution am Report-Ende in jedem Fall Pflicht

**Realistisches Budget für Datenquellen selbst:** 0–500 €/Monat.
**Realistisches Budget für Integration:** 1–3 Developer-Monate für Phase 1.

---

## Wer hat wie viel davon heute?

Zum Vergleich: was bieten deutsche Konkurrenten (schätzend, öffentliche Demos).
**Erweitert 2026-04-27** um BBSR, K.A.R.L., on-geo, EnviroTrust, docestate —
volle Recherche siehe [`MARKET_REALITY_DE_2026.md`](MARKET_REALITY_DE_2026.md).

| Anbieter | Bodenbewegung | Altlasten | Hochwasser | Radon | Bergbau | Naturgefahren-Mix | Preis | Modell |
|---|---|---|---|---|---|---|---|---|
| **Bodenbericht heute** | ✅ EGMS, gemessen | ❌ | ❌ | ❌ | ❌ | ❌ | €0 (Lead-Magnet) | B2C-PDF |
| **Bodenbericht Phase 1 (geplant)** | ✅ | ✅ (Top5) | ✅ | ✅ | ✅ | (siehe BBSR) | ?€ | B2C-PDF |
| **BBSR GIS-ImmoRisk** | ❌ | ❌ | (Starkregen) | ❌ | ❌ | ✅ Hitze/Erdbeben/Waldbrand/Hagel/Sturm/Starkregen | gratis | staatlich, B2C-Web |
| **K.A.R.L.® TAXO** (Köln.Assekuranz / on-geo) | ❌ (modelliert) | ❌ | ✅ | ❌ | ❌ | ✅ + EU-Taxo + CMIP6 | B2B Enterprise | B2B-API |
| **on-geo Lora** | ❌ | teilweise | teilweise | ❌ | ❌ | teilweise | B2B-Software | 95 % aller DE-Banken |
| **EnviroTrust** | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ Flut/Hitze/Sturm/Waldbrand/Luft | B2B | Asset Manager |
| **docestate.com** | ❌ | ✅ (pro BL) | ❌ | ❌ | ❌ | ❌ | €30–100 | B2C-Web |
| Avista | ❌ | ✅ (DE-weit) | ✅ | ❌ | ❌ | ✅ | €40–90 | B2C-PDF |
| BuildersOnline | teilweise | ✅ | ✅ | ✅ | ✅ | ✅ | €50–120 | B2C-PDF |
| Groundsure (UK) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | £80–180 | B2C-PDF |
| FunderConsult (NL) | ✅ (nur A–E-Label) | ❌ | ❌ | – | – | – | €7,95 | B2C-Web |

**Lesart:**

- **Naturgefahren-Mix in DE ist nicht mehr Wachstumsfeld** — BBSR liefert
  6 Layer gratis. Wer für sowas zahlen soll, fragt: „Warum, wenn der
  Bund's gratis macht?"
- **B2B-Banken-Schiene ist zu** — on-geo sitzt drin, K.A.R.L. ist
  EU-Taxonomie-zertifiziert.
- **Bodenbewegung mit Zeitreihen-Tiefe** ist der einzige Layer, den
  niemand sonst hat. K.A.R.L. nutzt Modelle, BBSR aggregierte Karten.
- **Altlasten DE-weit + günstig** ist eine echte Lücke (docestate ist
  landesspezifisch und teuer).

Unser Alleinstellungs-Merkmal nach Phase 1 = **EGMS-Tiefe (gemessen, nicht
modelliert) + DACH-Altlastenlage in der Breite + Preispunkt unter
docestate** — falls wir bei Avista-Parität bleiben.

**Achtung:** Strategiefrage Avista-Parität vs. Soil-Act/InSAR-Pivot ist
**offen** (siehe `PLAN_GEOFORENSIC_DE.md` §7). Falls Pivot: Phase-1-Liste
oben ist deutlich kürzer (Hochwasser + Radon + Bergbau + Altlasten, der
Rest fällt weg, weil BBSR ihn gratis macht).

---

## Vorschlag: Reihenfolge für morgen

Nicht alles gleichzeitig. Meine Empfehlung für die nächsten 2 Monate:

1. **Woche 1-2:** Pestizide (ESDAC) + Radon (BfS) — beides tief, geringer Aufwand
2. **Woche 3-5:** Hochwasser (EU-HWRM + 3 BL ÜSG)
3. **Woche 6-8:** Altlasten (NRW + BW + BY) — bringt den größten Impact
4. **Woche 9-10:** Erdbeben + Bergbau — rundet Groundsure-Look ab
5. **Ab Monat 3:** Cozy-Produktseite als Paid-Frontend aufbauen, alle Daten rein,
   Stripe-Flow live

---

## Zu klärende Fragen vor Start Phase 1

1. **Lizenz-Check BGR/Länder:** Commercial OK bei dl-de/by-2.0? (memory sagt
   BGR BBD License noch offen, E-Mail an BBD@bgr.de nie beantwortet?)
2. **Hosting-Strategie:** Bleibt alles auf Contabo, oder getrennte Services
   (eigenes "Data-API-Microservice"-Setup)?
3. **Budget-Frage Altlasten:** Sind wir bereit für 3-5 Wochen Dev-Aufwand pro
   Bundesland, oder starten wir mit **einem** (NRW) und wachsen organisch?
4. **Attribution im Report:** Heute nur Copernicus attribuiert. Bei 8+ Quellen
   braucht's eine saubere Attribution-Sektion pro Layer.
