# VISUALS_ROLLOUT_PLAN.md — Implementations-Plan für das Visuals-Paket

**Stand:** 2026-04-30, nach Phase A+B (ProofTrailAgents-Migration + Country-Routing + Landing-USP-Block).
**Bezug:** Cozy hat ein Visuals-Paket geliefert in `docs/visuals/` — 6 Komponenten, Datenkontrakt, Reference-SVGs.
**Zweck dieses Docs:** Self-contained Plan, der ohne den Kontext der vorigen Chat-Session ausreicht. Eine neue Claude-Session liest dies + die Spec + die Reference-SVGs und kann mit Phase V.1 starten.

---

## 1. Kontext und Ausgangslage

### 1.1 Was das Paket enthält

Im Verzeichnis `docs/visuals/`:
- `README.md` — Reading-Order und Spielraum
- `SPEC_VISUALS.md` — vollständige Architektur-Spec mit Tier-Logik und Akzeptanzkriterien
- `data_contract.json` — JSON-Schema pro Komponente
- `example_payload.json` — komplett ausgefüllter Datensatz für Schulstraße 12, 76571 Gaggenau
- `reference_svgs/01_risk_dashboard.svg` bis `06_neighborhood_histogram.svg` — Design-Source-of-Truth, 680 px ViewBox

### 1.2 Was wir liefern sollen — die 6 Komponenten

| # | Komponente | Tier | Free-Report | Premium | Frontpage-Demo |
|---|---|---|---|---|---|
| 1 | Risiko-Dashboard | 1 | voll | voll | ja |
| 2 | Grundstück-im-Kontext (Karte) | 1 | voll | voll | ja |
| 3 | Velocity-Zeitreihe + Niederschlag | 1 | Teaser (verschwommen) | voll | ja |
| 4 | Bodenkontext-Stapel | 2 | Teaser | voll | ja |
| 5 | Korrelations-Spinne | 2 | Teaser | voll | ja |
| 6 | Nachbarschafts-Vergleich | 1 | Teaser | voll | ja |

### 1.3 Codebasis-Stand zum Start

Das Repo ist `geoforensic-app` (`github.com/8endit/geoforensic-app`). Aktuelle Struktur, soweit für Visuals relevant:

- `backend/app/full_report.py` — **FPDF-basierter Vollbericht**, 12 Sektionen
- `backend/app/html_report.py` — **Chrome-Headless-Teaser**, 13 Locked-Cards (HTML→PDF via `pdf_renderer.py`)
- `backend/app/soil_data.py` — SoilDataLoader (SoilGrids, LUCAS, CORINE, HRL Imperviousness, WRB)
- `backend/app/soil_directive.py` — 16-Descriptor EU-Bodenrichtlinie
- `backend/app/pesticides_data.py` — LUCAS NUTS2
- `backend/app/altlasten_data.py` — PDOK Bodemloket NL + CORINE-Proxy DE
- `backend/app/slope_data.py` — Multi-Scale Slope via OpenTopoData
- `backend/app/flood_data.py` — BfG HWRM
- `backend/app/mining_nrw.py` — NRW Bergbau
- `backend/app/kostra_data.py` — DWD KOSTRA
- `backend/app/rfactor_data.py` — ESDAC R-Faktor
- `backend/app/routers/leads.py` — Pipeline-Orchestrator (`POST /api/leads`)
- `landing/index.html` — Bodenbericht-Landing mit 16-Descriptor-USP-Block
- `docs/DATA_PROVENANCE.md` — kanonische Datenquellen-Übersicht

Cozy-Frontend lebt in **eigenem Repo** `github.com/8endit/cozy-frontend`, NICHT als Subdir hier.

---

## 2. Architektur-Entscheidungen

### 2.1 PDF-Render-Strategie für den Vollbericht

**Konflikt:** Spec sagt „Chrome Headless rendert HTML mit eingebetteten SVGs ins PDF". Unser Vollbericht ist aber FPDF-basiert, der Teaser ist Chrome-Headless.

**Entscheidung:** Pragmatischer Hybrid-Pfad statt Refactor.

| Bericht | Render-Pfad | SVG-Einbettung |
|---|---|---|
| Teaser (`html_report.py`) | Chrome-Headless HTML→PDF | SVG direkt im HTML, Jinja füllt Werte |
| Vollbericht (`full_report.py`) | FPDF | SVG → cairosvg → PNG → `pdf.image()` |

**Begründung:** FPDF→HTML-Refactor wäre ein Sprint für sich (Layout, Page-Breaks, Hochformat-Logik). cairosvg+PNG-Bridge ist 1 Tag Arbeit, akzeptable Auflösung wenn 2× DPI gerendert wird. Wenn der Vollbericht später aus anderen Gründen sowieso auf HTML umzieht, sind die SVG-Templates weiterverwendbar — nichts wird obsolet.

**Konkret:**
- SVG-Templates leben in `backend/templates/visuals/*.svg.jinja2`
- Helper-Modul `backend/app/visual_renderer.py` mit zwei Methoden:
  - `render_svg(name, data) -> str` für Chrome-Headless-Pfad
  - `render_png(name, data, dpi=200) -> bytes` für FPDF-Pfad (cairosvg)
- Beide nehmen denselben Daten-Dict, Quelle-of-Truth ist das SVG-Template

### 2.2 Frontend-Komponenten

Spec sagt `frontend/src/components/visuals/` — wir setzen das in **`8endit/cozy-frontend` Repo** um, nicht in geoforensic-app. Dort entsteht ein neues Verzeichnis `components/visuals/` mit React-JSX-Komponenten.

Tokens werden in `geoforensic-app/shared/visual_tokens.json` definiert — von beiden Seiten lesbar (Backend per `import json`, Frontend per `import tokens from "../shared/visual_tokens.json"` mit symlink oder build-step).

**Alternative:** Tokens als npm-package `@geoforensic/visual-tokens` veröffentlichen — overkill für jetzt, aber merken wenn das Repo wächst.

### 2.3 Daten-Pipeline

Der Daten-Kontrakt (`data_contract.json`) erwartet Felder, die unsere Pipeline aktuell **nicht** erzeugt. Die müssen im Vorlauf nachgerüstet werden:

| Feld | Stand | Aufgabe |
|---|---|---|
| `risk_dashboard.burland_class` (1–6) | nicht vorhanden | Modul `burland_classifier.py` aus Velocity + Trend ableiten |
| `risk_dashboard.overall_grade` (A–E) | nicht vorhanden | Logik aus Burland + Datenqualität + PSI-Anzahl |
| `property_context_map.building_footprint.polygon` (LoD2) | nicht vorhanden | OpenStreetMap building-Polygon aus Overpass als Stand-In; LoD2 NRW als Phase C |
| `velocity_timeseries.correlation_coefficient` (Pearson r) | nicht vorhanden | scipy.stats.pearsonr aus EGMS-Zeitreihe + DWD KOSTRA-Niederschlag |
| `soil_context_stack.layers[].bedrock` (Festgestein) | nicht vorhanden | `geology.py` aus ProofTrailAgents migrieren (BGR GUEK200) |
| `correlation_radar.axes[swelling_clay]` (Quelltonanteil) | nicht vorhanden | aus SoilGrids Clay% ableitbar als grobe Approximation |
| `correlation_radar.axes[groundwater]` | nicht vorhanden | LGRB BW Hydrogeologie für BW; andere BL als Phase C |
| `neighborhood_histogram.bins` | nicht vorhanden, einfach | aus existing EGMS-Query in 500m-Radius bin-en (numpy.histogram) |

---

## 3. Vorlauf-Sprint (vor Visuals selbst)

Diese Mini-Phase schließt die Daten-Lücken die für Tier-1-Visuals nötig sind. Tier-2-Lücken werden später adressiert.

### V.0.1 — Burland-Klassifikator
- Neues Modul `backend/app/burland_classifier.py`
- Input: mean_velocity, max_velocity, trend_slope, psi_count
- Output: class (1–6), label (stabil/leicht/moderat/auffällig/erheblich/kritisch), description
- Quelle für Klassen-Schwellen: Burland 1995 (Settlement-of-buildings classification)
- Akzeptanz: Smoke-Test mit Beispielwerten aus `example_payload.json` ergibt `class=2, label=leicht`

### V.0.2 — Pearson-Korrelation EGMS × Niederschlag
- In `flood_data.py` oder neuem `backend/app/correlations.py`
- Input: PSI-Zeitreihe (10 Punkte), DWD-Niederschlag-Zeitreihe (10 Punkte)
- Output: Pearson r, p-Value
- Akzeptanz: Beispiel aus payload ergibt `r ≈ 0.71`

### V.0.3 — `geology.py` migrieren
- Aus `ProofTrailAgents/geoforensic/backend/reports/geology.py`
- Quelle: BGR GUEK200 WMS GetFeatureInfo
- Output: dict mit Festgestein-Typ, Verwitterungstiefe, etc.
- Country-Routing: nur DE, sonst `available=False`
- Smoke-Test gegen Live-Endpoint

### V.0.4 — Building-Footprint via OSM Overpass
- Neues Modul `backend/app/building_footprint.py`
- Query Overpass nach `way[building](around:30,lat,lon)`
- Pick das Polygon das den Adress-Punkt enthält (oder das nächste, falls Geocoding ungenau)
- Output: list of [lon, lat] coordinate pairs
- Fallback: kein Footprint → Karte zeigt nur Kreis-Marker am Adress-Centroid
- LoD2 (NRW etc.) als Phase C — kein Blocker

### V.0.5 — Datenkontrakt-Builder
- Neues Modul `backend/app/visual_payload.py` mit Funktion `build_payload(lat, lon, address, country_code) -> dict`
- Aggregiert: SoilDataLoader-Output + soil_directive + slope + altlasten + flood + KOSTRA + EGMS + neue Module aus V.0.1–V.0.4
- Output: Payload exakt wie in `example_payload.json`
- Akzeptanz: Schema-Validierung gegen `data_contract.json` (mit jsonschema package)

### V.0.6 — Provenance-Felder pro Pipeline-Output (Honesty-Layer)

Hintergrund: Wir machen kein ML-Downscaling, keine Daten-Fusion, keine eigene Kalibrierung. Was wir liefern ist solides Engineering über offizielle EU-Raster (IDW, Window-Mean, Multi-Scale, Country-Routing). Statt das zu verbergen oder zu übertreiben, soll jeder Datenpunkt ein **Provenance-Feld** mitführen, sodass die Visuals-Templates ehrlich-präzise Statements rendern können statt nackte Werte.

**Konkret:** Jedes Modul produziert zusätzlich ein `data_provenance` dict pro Output-Wert mit:
- `source` — Datenquelle als String (z.B. `"ESDAC Panagos 2015"`, `"SoilGrids 250m"`, `"OpenTopoData SRTM"`)
- `resolution_m` — räumliche Auflösung der Quelle in Metern (z.B. `1000`, `250`, `30`)
- `sample_count` — Anzahl Datenpunkte die in den Wert eingingen (z.B. PSI-Punkte, LUCAS-Probepunkte, CORINE-Pixel im 100 m-Window)
- `method` — Aggregations-Methode (z.B. `"IDW über 3 Nachbarn"`, `"Window-Mean 100 m"`, `"Multi-Scale steepest 50/150/500 m"`, `"Single-Pixel"`)
- Optional: `nearest_distance_m`, `regional_scope` (z.B. `"NUTS2 DE12"`)

**Output-Format-Beispiel:**

```json
{
  "value": 502,
  "unit": "MJ·mm/(ha·h·yr)",
  "data_provenance": {
    "source": "ESDAC Panagos 2015",
    "resolution_m": 1000,
    "sample_count": 1,
    "method": "Single-Pixel"
  }
}
```

**Wo das eingebaut wird:**
- `rfactor_data.py:RFactorResult` bekommt `data_provenance` field
- `slope_data.py:fetch_slope` Output erweitert um `data_provenance`
- `soil_data.py:SoilDataLoader.query_full_profile` — pro Wert ein Provenance-Block
- `pesticides_data.py:PesticidesResult` bekommt `data_provenance` mit `regional_scope: "NUTS2 ..."`
- `soil_directive.py` propagiert Provenance der eingehenden Module mit

**Visuals-Template-Verwendung:** Templates können dann statt `502 MJ·mm/(ha·h·yr)` etwas rendern wie `502 MJ·mm/(ha·h·yr) — ESDAC 1 km`. Oder als Tooltip: „Quelle: ESDAC Panagos 2015. Auflösung: 1 km. Methode: Pixel-Lookup."

**Akzeptanz:**
- Smoke-Test: `query_soil_directive(48.78, 9.18, "de")` enthält pro Datenwert ein `data_provenance`-Dict
- DATA_PROVENANCE.md §10 ergänzt um Format-Spezifikation der Provenance-Felder
- KEIN Modul behauptet falsche Methodik — `method: "Pearson r EGMS x DWD"` nur wenn V.0.2 wirklich gerechnet, sonst nicht setzen

**Wichtig:** Dieser Step macht uns NICHT genauer als die Rohdaten. Er macht uns **transparenter** — Käufer kann jeden Wert gegen die offizielle EU-Quelle nachprüfen. Das ist eine Vertrauens-Position gegen K.A.R.L./on-geo (Black-Box-ML) und gegen docestate (Behörden-Vermittler ohne Daten-Auflösung).

---

## 4. Visuals-Sprint Phasen

### Phase V.1 — Foundation (geteilte Tokens + Visuals-Inbox einchecken)

**Outputs:**
- `shared/visual_tokens.json` mit Farbcodes, Schwellwerten, Schriftgrößen aus Spec §3
- `docs/visuals/` umziehen nach `docs/visuals/` und committen (damit Cozy + Backend gleichermaßen Zugriff haben über GitHub)
- `backend/app/visual_renderer.py` Stub mit `render_svg()` und `render_png()`
- `backend/templates/visuals/` Verzeichnis anlegen

**Akzeptanz:**
- `tokens.json` ist gültiges JSON, alle Farben aus Spec §3 abgedeckt
- `visual_renderer.py` rendert ein Hello-World-SVG erfolgreich zu PNG via cairosvg
- `cairosvg` ist in `requirements.txt` und im Dockerfile (`libcairo2` ist schon drin)

### Phase V.2 — Tier-1-Templates (Free-Report-Visuals)

**Outputs:**
- `backend/templates/visuals/risk_dashboard.svg.jinja2`
- `backend/templates/visuals/property_context_map.svg.jinja2`
- Im `html_report.py` (Teaser) eingebunden — voll sichtbar (kein Blur)
- Im `full_report.py` via PNG-Bridge eingebunden — voll sichtbar
- Smoke-Test mit Schulstraße-12-Daten ergibt rendered PDF mit beiden Visuals

**Akzeptanz:**
- Beide Visuals matchen die Reference-SVGs visuell (Spot-Check)
- Schwellen-Logik aus Spec §4.1 und §4.2 implementiert (Burland-Hintergrundfarbe, PSI-Punkte mit Mindestabstand 8px)
- Bei fehlenden Daten: Boxen mit "—", PSI-Hinweis "Sparse Data" wenn <10 Punkte
- WeasyPrint-Kompatibilität: SVG funktioniert ohne JavaScript und ohne externe CSS

### Phase V.3 — Tier-2-Templates + Teaser-Wrapper

**Outputs:**
- 4 weitere Templates: `velocity_timeseries.svg.jinja2`, `soil_context_stack.svg.jinja2`, `correlation_radar.svg.jinja2`, `neighborhood_histogram.svg.jinja2`
- `backend/templates/visuals/_teaser_wrapper.svg.jinja2` — wrappt ein Sub-SVG mit `feGaussianBlur` Filter + Schloss-Icon-Overlay
- Im Teaser eingebunden: alle 6 Visuals; Tier-2 mit Wrapper, Tier-1 ohne
- Im Vollbericht eingebunden: alle 6 voll sichtbar (Premium)

**Akzeptanz:**
- Velocity-Zeitreihe zeigt Trendlinie aus linearer Regression, Korrelations-r im Footer
- Korrelations-Spinne normiert Achsen auf 0–5; bei fehlender Achse "n/a" statt Polygon-Punkt
- Bodenkontext-Stapel skaliert Schichthöhen proportional, Grundwasserlinie nur wenn Wert da
- Histogramm zeigt eigene-Adresse-Marker mit gestrichelter Linie

### Phase V.4 — Vollbericht-FPDF-Integration polish

**Outputs:**
- `visual_renderer.render_png(name, data, dpi=200)` produziert druckfähige PNGs (200 DPI)
- `full_report.py` ruft den Renderer pro Sektion und bettet das PNG via `pdf.image()` ein
- Premium-Vollbericht hat alle 6 Visuals an passender Stelle (z.B. Risiko-Dashboard auf Seite 1, Karte auf Seite 2)

**Akzeptanz:**
- Generierter Vollbericht-PDF in DIN A4 mit allen 6 Visuals lesbar
- PNG-Auflösung scharf bei 200% Zoom
- PDF-Größe < 1 MB pro Bericht (Komprimierung via `pdf.image(quality=85)`)

### Phase V.5 — Frontend-Komponenten (Cozy-Frontend Repo)

**Outputs in `github.com/8endit/cozy-frontend`:**
- `components/visuals/RiskDashboard.tsx`, `PropertyContextMap.tsx`, `VelocityTimeseries.tsx`, `SoilContextStack.tsx`, `CorrelationRadar.tsx`, `NeighborhoodHistogram.tsx`
- Jede Komponente nimmt Props passend zum jeweiligen Datenkontrakt
- Selbe SVG-Markup-Struktur wie Backend-Templates (Stylelint-Regel falls möglich)
- Tokens-Import via `@geoforensic/visual-tokens` ODER lokale Kopie aus geoforensic-app

**Akzeptanz:**
- Storybook-Geschichten pro Komponente mit Beispiel-Props
- Hover-Tooltips auf Datenpunkten
- Responsive: ViewBox-Width skaliert auf Container, Mindesthöhe respektiert

### Phase V.6 — Frontpage-Demo

**Outputs in cozy-frontend Repo:**
- Neue Seite oder Sektion `/demo`
- Statische Beispieldaten Schulstraße 12 (aus `example_payload.json`)
- Slider-Interaktion: Velocity-Slider passt Burland-Klasse + Zeitreihe + Histogramm an, Niederschlags-Slider verformt Korrelations-Spinne
- Demo-Wasserzeichen / Banner „Beispiel-Grundstück"
- Animation mit Framer Motion oder CSS-Transitions

**Akzeptanz aus Spec §6:**
- Lädt in <2 s auf 4G
- iOS Safari, Chrome Android, Firefox Desktop ohne JS-Crash
- Mobile: Slider auf Touch funktional
- Demo-Charakter klar erkennbar

### Phase V.7 — Documentation + Provenance Update

**Outputs:**
- `docs/DATA_PROVENANCE.md` ergänzt um neue Module (Burland, Pearson, geology, building_footprint)
- `CLAUDE.md` § Working-in-Production aktualisiert
- `STATUS_<datum>.md` schreiben

---

## 5. Reihenfolge mit Abhängigkeiten

```
V.0.1 Burland     ─┐
V.0.2 Pearson     ─┤── parallel ──┐
V.0.3 geology     ─┤              │
V.0.4 footprint   ─┘              │
                                  ↓
V.0.5 Payload-Builder ──→ V.0.6 Provenance-Felder ──→ V.1 Foundation ──→ V.2 Tier-1
                                                                              │
                                                                          V.3 Tier-2
                                                                              │
                                                                          V.4 Vollbericht-FPDF
                                                                              │
                                                                          V.5 Frontend-React
                                                                              │
                                                                          V.6 Frontpage-Demo
                                                                              │
                                                                          V.7 Docs
```

**Critical path:** V.0.1–V.0.6 müssen vor V.1. V.5 + V.6 sind das Cozy-Frontend, können parallel zu V.4 laufen.

V.0.6 ist explizit **nach** V.0.5 — es nutzt die im Builder aggregierten Pipeline-Outputs als Anker und reichert sie an. V.0.6 könnte technisch parallel zu V.0.1–V.0.4 laufen (jedes neue Modul liefert direkt Provenance mit), aber die Konsolidierung der bestehenden Module geht sauberer wenn der Builder schon steht.

---

## 6. Risiken und Stolperfallen

### 6.1 cairosvg auf Windows
`cairosvg` braucht Cairo-Binaries. Auf dem VPS-Container ist `libcairo2` schon im Dockerfile (für WeasyPrint). Auf Windows-Dev kann es Pfad-Probleme geben — falls das auftritt, GTK-Runtime installieren oder auf reportlab/svglib ausweichen.

### 6.2 LoD2 Building-Footprint
Spec erwartet LoD2-Polygon — wir nehmen erstmal OSM Overpass als Stand-In. Das gibt für die meisten DE-Adressen ein Polygon, ist aber simpler als LoD2 (kein Höhenprofil, weniger detailreich). Cozy soll das wissen, könnte Reference-SVG entsprechend anpassen.

### 6.3 Schulstraße 12 Geocoding
`example_payload.json` hat Lat/Lon `48.80123, 8.32456` — vor V.0.5 mit Nominatim verifizieren, falls die Koords falsch sind, Daten neu berechnen. Sonst bricht der Demo-Sample.

### 6.4 SVG → PNG Color Accuracy
Cairo kann ein paar SVG-Features nicht (z.B. `feGaussianBlur` Filter). Tier-2-Teaser-Wrapper mit Blur funktioniert im HTML→Chrome-Pfad, im FPDF-PNG-Pfad muss der Blur **vor** der Konvertierung als Pre-Processing rein (z.B. PIL.ImageFilter.GaussianBlur). Im Vollbericht (Premium) sind Tier-2 ohnehin nicht geblurrt, also irrelevant.

### 6.5 ProofTrailAgents-Endpoint-Drift
Wir haben in der vorigen Session festgestellt, dass viele Behörden-Endpoints aus ProofTrailAgents tot sind (PDOK Bodemloket, LANUV NRW, LUBW). Bei V.0.3 (geology aus PTA) wird wahrscheinlich der BGR GUEK200-Endpoint auch geprüft und ggf. korrigiert werden müssen.

---

## 7. Was nach diesem Sprint offen bleibt

- **LoD2-Building-Footprints für DE-Bundesländer** mit eigenen Diensten (NRW, BW, BY, SN — nicht alle haben Public-WFS)
- **LGRB BW Hydrogeologie** für Grundwasser-Achse in der Korrelations-Spinne — andere Bundesländer haben eigene Quellen
- **NL-Pendant für die Visuals** — alle 6 müssen NL-i18n bekommen wenn wir den NL-Markt bedienen (eigener Sprint analog Phase C)
- **Vollbericht-Refactor FPDF→HTML** — wenn die PNG-Bridge sich als zu unscharf erweist oder Layout-Beschränkungen drücken

---

## 8. Wie eine neue Claude-Session damit startet

**Empfohlene erste Anweisung an die nächste Session:**

> Lies `docs/visuals/SPEC_VISUALS.md` und `docs/VISUALS_ROLLOUT_PLAN.md`. Bestätige dass du den Plan verstehst, dann fang an mit Phase V.0.1 (Burland-Klassifikator).

**Voraussetzung:** Phase A+B-Updates müssen auf dem VPS gepullt sein. Dieser Visuals-Sprint baut auf den 13 aktiven Datenmodulen aus der vorigen Phase auf — falls KOSTRA/CORINE/NUTS2-Files noch nicht auf VPS sind, lokal arbeiten reicht für die Implementation, aber der erste echte End-to-End-Test (V.0.5 Smoke-Test mit Live-Adresse) braucht die Files auf Server oder Dev-Mount.

**Datenquellen der Wahrheit:**
- `docs/visuals/SPEC_VISUALS.md` — was zu bauen ist
- `docs/visuals/data_contract.json` — wie die Daten aussehen
- `docs/visuals/reference_svgs/` — wie's optisch aussieht
- `docs/visuals/example_payload.json` — Schulstraße 12 als Smoke-Test-Adresse
- `docs/DATA_PROVENANCE.md` — was unsere Pipeline aktuell schon liefert

**Bei Unklarheiten:** Annahme treffen, in Commit-Message dokumentieren, weitermachen. Cozy ist Designhoheit für die Visuals-Optik, Backend-Architektur ist Claude-Code-Spielraum.
