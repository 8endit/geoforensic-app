# VISUALS_ROLLOUT_PLAN.md — Implementations-Plan für das Visuals-Paket

**Stand:** 2026-05-01, nach Plan-Review.
**Bezug:** Cozy hat ein Visuals-Paket geliefert in `docs/visuals/` — 6 Komponenten, Datenkontrakt, Reference-SVGs.
**Zweck dieses Docs:** Self-contained Plan, der ohne den Kontext der vorigen Chat-Session ausreicht. Eine neue Claude-Session liest dies + die Spec + die Reference-SVGs und kann mit Phase V.0.1 starten.

**Architektur-Update gegenüber Vorversion (2026-04-30):**
- Vollbericht zieht von **FPDF auf Chrome-Headless HTML→PDF** um (V.4 = Refactor, nicht Polish). Begründung in §2.1.
- `cairosvg`-PNG-Bridge entfällt komplett. SVGs werden in beiden Reports direkt im HTML eingebettet (vector statt raster).
- V.4.5 (FPDF-Polish) ist gestrichen — Premium-Look wird über CSS Paged Media im neuen HTML-Pfad erreicht und ist Teil von V.4.
- Neue Phase V.4.7 — `bodenbericht.de` Landing-Page-Polish (außerhalb der PDFs, aber im selben Visuals-Sprint).
- V.0.6 Provenance-Felder werden **additiv** spezifiziert (kein breaking change am Pipeline-Output).
- V.1 erweitert um Font-Subsetting + frühe cairosvg/Chrome-Smoke-Tests der Reference-SVGs.
- V.2 (Karte) ergänzt um realen Basemap-Layer (vorher Schema-Layout).
- Visual-Regression-Tests, Sparse-Data-Gesamt-Verhalten und CMYK-Profile in den Akzeptanzkriterien ergänzt.

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

- `backend/app/full_report.py` — **FPDF-basierter Vollbericht**, 12 Sektionen → wird in V.4 ersetzt durch HTML-Pfad
- `backend/app/html_report.py` — **Chrome-Headless-Teaser**, 13 Locked-Cards (HTML→PDF via `pdf_renderer.py`) → bleibt
- `backend/app/pdf_renderer.py` — Chrome-Headless-Wrapper mit WeasyPrint-Fallback → wird in V.4 wiederverwendet
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
- `landing/index.html` — Bodenbericht-Landing mit 16-Descriptor-USP-Block → in V.4.7 visuell aufgewertet
- `docs/DATA_PROVENANCE.md` — kanonische Datenquellen-Übersicht

Cozy-Frontend lebt in **eigenem Repo** `github.com/8endit/cozy-frontend`, NICHT als Subdir hier.

---

## 2. Architektur-Entscheidungen

### 2.1 Render-Strategie für beide Reports — Chrome-Headless einheitlich

**Entscheidung (2026-05-01):** Beide Reports rendern über Chrome-Headless HTML→PDF. Vollbericht zieht von FPDF um. Keine PNG-Bridge mehr.

**Warum nicht FPDF behalten:**
- Magazin-Niveau-Typografie (Sentient/Geist Mono mit Kerning, Ligaturen, Hyphenation) ist in FPDF brüchig — woff2-Fonts müssen explizit registriert werden, Italic/Extralight-Varianten kollidieren regelmäßig.
- Echte Layout-Features (Multi-Column-Flow, Textfluss um Bilder, sauberer Page-Break vor Section-Header, automatische Widow/Orphan-Kontrolle) liefert nur CSS Paged Media.
- SVGs würden über `cairosvg → PNG → pdf.image()` gerasterisiert — Vektor-Schärfe verloren, Dateigröße steigt, Filter-Effekte (`feGaussianBlur` für Tier-2-Teaser) brauchen PIL-Pre-Processing-Workaround.
- Cover-Page, 4-Block-Struktur, dezenter Page-Footer, QR-Code, Provenance-Block am Ende — alles in CSS in einem Bruchteil des Aufwands von FPDF-`set_xy()`-Hand-Layout.

**Warum Chrome-Headless statt WeasyPrint primär:**
- Chrome-Headless ist im Repo schon produktiv (`pdf_renderer.py`, Teaser läuft seit April darüber).
- CSS-Paged-Media-Coverage in Chromium ist breiter als in WeasyPrint (Page-Counter, Running-Headers, `@page :first`).
- WeasyPrint bleibt als Fallback im Renderer drin (für CI ohne Chromium).

**Konkret:**
- SVG-Templates in `backend/templates/visuals/*.svg.jinja2` werden direkt in das HTML-Template per `{% include %}` eingebettet (inline SVG). Kein PNG-Zwischenschritt.
- `backend/app/visual_renderer.py` hat **eine** Methode: `render_svg(name, data) -> str`. Beide Reports nutzen sie.
- Vollbericht-HTML-Templates leben in `backend/templates/full_report/` — Cover, Block-Trennseiten, Sektionen, Footer. CSS in `backend/static/full_report.css` mit `@page`-Regeln.
- Print-CSS hartkodiert Farben in sRGB; CMYK-Profile-Embedding ist optional (siehe Akzeptanz V.4).

| Bericht | Render-Pfad | SVG-Einbettung | Status nach V.4 |
|---|---|---|---|
| Teaser (`html_report.py`) | Chrome-Headless HTML→PDF | inline SVG via Jinja-Include | bleibt |
| Vollbericht (`full_report.py`) | Chrome-Headless HTML→PDF | inline SVG via Jinja-Include | refactored |

`full_report.py` wird umgeschrieben zu einer dünnen Funktion, die Daten aggregiert und das HTML-Template rendert. Die FPDF-Logik wird gelöscht (kein Backwards-Compat-Shim — in `routers/leads.py` ist nur eine Aufruf-Stelle).

### 2.2 Frontend-Komponenten

Spec sagt `frontend/src/components/visuals/` — wir setzen das in **`8endit/cozy-frontend` Repo** um, nicht in geoforensic-app. Dort entsteht ein neues Verzeichnis `components/visuals/` mit React-JSX-Komponenten.

Tokens werden in `geoforensic-app/shared/visual_tokens.json` definiert — von beiden Seiten lesbar (Backend per `import json`, Frontend per `import tokens from "../shared/visual_tokens.json"` mit symlink oder build-step).

**Alternative:** Tokens als npm-package `@geoforensic/visual-tokens` veröffentlichen — overkill für jetzt, aber merken wenn das Repo wächst.

### 2.3 Layout-Strategie — zwei eigene Reports, gemeinsame Bausteine

Free und Premium sind zwei **unterschiedliche Use-Cases**, also zwei eigene Layouts. Aber sie teilen Datenkontrakt, Visual-Tokens und die 6 SVG-Komponenten.

| Aspekt | Free / Teaser (`html_report.py`) | Premium / Vollbericht (`full_report.py` nach V.4) |
|---|---|---|
| Zieldomain | bodenbericht.de | geoforensic.de (geplant) |
| Käufer-Stand | noch nicht konvertiert, Lead-Magnet | bezahlt 19–199 EUR, Käufer-Dokument |
| Funktion | Marketing-Funnel, Conversion treiben | Tiefe + Provenance, Nachprüfbarkeit |
| Render-Pfad | Chrome-Headless HTML→PDF | Chrome-Headless HTML→PDF (refactored in V.4) |
| Design-System | bodenbericht-Tailwind (lighter, freundlich) | Cozy-Designsystem (Schwarz/Grün, professionell) |
| Locked-Cards | ja, 13 Stück mit Lock-Pille + Schloss-Icon | nicht vorhanden, alles voll |
| Cover-Page | „Bodenbericht — Kostenlose Kurzfassung", Ampel/GeoScore dominant | „GeoForensic Vollbericht", schwarz-grün, Adresse + Bericht-Nr. + QR |
| Section-Header | hellgrün, Lock-Cards, „IM VOLLBERICHT ENTHALTEN"-Strap | dunkler Akzent, 4 thematische Blöcke (Risiken / Untergrund / Bodenchemie / Bewertung) |
| Footer | „Auf die Warteliste"-CTA + Stripe-Link | Provenance-Block + Datenquellen + Disclaimer |
| Branding | bodenbericht.de Logo | GeoForensic Logo (Cozy-Design) |
| Typografie | system-fonts + Tailwind-Default | Sentient (display) + Geist Mono (UI/data), woff2 inline |

**Was beide teilen:**
- `shared/visual_tokens.json` (Farben, Schwellen, Typografie-Skala) — identisch
- 6 Visualisierungs-SVG-Templates (Risiko-Dashboard, Karte, Velocity, Bodenstapel, Radar, Histogramm) — identisch, nur im Free mit `feGaussianBlur`-Wrapper für Tier-2
- Datenkontrakt (`example_payload.json`-Schema) — identisch
- `visual_renderer.render_svg()` — identische Aufrufstelle aus beiden Reports
- Frontend-Komponenten in `cozy-frontend` Repo nutzen exakt selbe SVG-Struktur

**Konsequenz für die Umsetzung:** SVG-Templates werden in V.2/V.3 einmal gebaut und in beiden Reports per `{% include %}` verwendet. Das HTML-Wrapper-Layout (Cover, Section-Wrap, Footer) ist getrennt — Free in `landing`-Tailwind-Style, Premium in Cozy-Style.

### 2.4 Daten-Pipeline

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

### V.0.6 — Provenance-Felder pro Pipeline-Output (Honesty-Layer, additiv)

Hintergrund: Wir machen kein ML-Downscaling, keine Daten-Fusion, keine eigene Kalibrierung. Was wir liefern ist solides Engineering über offizielle EU-Raster (IDW, Window-Mean, Multi-Scale, Country-Routing). Statt das zu verbergen oder zu übertreiben, soll jeder Datenpunkt ein **Provenance-Feld** mitführen, sodass die Visuals-Templates ehrlich-präzise Statements rendern können statt nackte Werte.

**Wichtig — additive Erweiterung, kein breaking change:** Existierende Felder bleiben unverändert. `data_provenance` wird als zusätzliches Dict pro Modul-Output ergänzt. Kein Caller muss angepasst werden, Templates können das Feld optional konsumieren. V.0.6 ist dadurch nicht critical-path: kann technisch parallel zu V.0.1–V.0.4 laufen, oder sogar nach V.1 nachgezogen werden ohne Visuals zu blockieren.

**Konkret:** Jedes Modul produziert zusätzlich ein `data_provenance` dict pro Output-Wert mit:
- `source` — Datenquelle als String (z.B. `"ESDAC Panagos 2015"`, `"SoilGrids 250m"`, `"OpenTopoData SRTM"`)
- `resolution_m` — räumliche Auflösung der Quelle in Metern (z.B. `1000`, `250`, `30`)
- `sample_count` — Anzahl Datenpunkte die in den Wert eingingen
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
- Existierende Tests laufen unverändert (keine breaking changes)
- DATA_PROVENANCE.md §10 ergänzt um Format-Spezifikation der Provenance-Felder
- KEIN Modul behauptet falsche Methodik — `method: "Pearson r EGMS x DWD"` nur wenn V.0.2 wirklich gerechnet, sonst nicht setzen

**Wichtig:** Dieser Step macht uns NICHT genauer als die Rohdaten. Er macht uns **transparenter** — Käufer kann jeden Wert gegen die offizielle EU-Quelle nachprüfen. Das ist eine Vertrauens-Position gegen K.A.R.L./on-geo (Black-Box-ML) und gegen docestate (Behörden-Vermittler ohne Daten-Auflösung).

---

## 4. Visuals-Sprint Phasen

### Phase V.1 — Foundation (Tokens, Renderer, Asset-Prep, Smoke-Tests)

**Outputs:**
- `shared/visual_tokens.json` mit Farbcodes, Schwellwerten, Schriftgrößen aus Spec §3
- `backend/app/visual_renderer.py` mit `render_svg(name, data) -> str` (Jinja-Render auf SVG-Templates)
- `backend/templates/visuals/` Verzeichnis anlegen
- `backend/templates/full_report/` Verzeichnis als Stub (wird in V.4 gefüllt)
- `backend/static/fonts/` mit subgesetzten woff2-Versionen von Sentient (display) + Geist Mono (UI):
  - Nur lateinische Glyphen + benötigte Symbole (μ, ², ³, →, etc.)
  - Embedding direkt in HTML als `@font-face` mit `data:` URI (kein Netzwerk-Hop beim Render, kein FOUT in Headless-Chrome)
  - Subset-Tool: `fonttools` `pyftsubset` als Build-Script in `backend/scripts/subset_fonts.py`
- `backend/static/css/tokens.css` — generierter CSS-Custom-Properties-Block aus `visual_tokens.json` (build-step in `subset_fonts.py` mitkippen oder eigenes `generate_tokens_css.py`)
- **Frühe Smoke-Tests der Reference-SVGs:**
  - `tests/visuals/test_reference_svgs.py` — rendert jede der 6 Reference-SVGs durch Chrome-Headless zu PDF und prüft, dass keine Render-Errors entstehen, dass `feGaussianBlur`, `mask`, `pattern`, `foreignObject` korrekt durchkommen
  - WeasyPrint-Fallback-Test parallel — wenn ein Feature in WeasyPrint scheitert aber in Chrome funktioniert, Trade-Off dokumentieren

**Akzeptanz:**
- `visual_tokens.json` ist gültiges JSON, alle Farben aus Spec §3 abgedeckt
- `tokens.css` wird automatisch aus JSON generiert (single source of truth)
- `visual_renderer.render_svg()` rendert ein Hello-World-SVG-Template erfolgreich
- Reference-SVG-Smoke-Tests grün auf Chrome-Headless; etwaige Inkompatibilitäten dokumentiert
- Subgesetzte Fonts liegen unter 40 KB pro Datei
- HTML-Test-Dokument mit beiden Fonts rendert in Chrome-Headless ohne Font-Substitution-Warning

### Phase V.2 — Tier-1-Templates (Free-Report-Visuals)

**Outputs:**
- `backend/templates/visuals/risk_dashboard.svg.jinja2`
- `backend/templates/visuals/property_context_map.svg.jinja2`
- **Karte mit realem Basemap-Layer:** statt Schema-Layout wird ein dezenter Tiles-Hintergrund (CartoDB Positron oder Stamen Toner Lite, getintet auf Cozy-Palette) hinter den PSI-Dots gerendert. Implementierung:
  - Server-side rendering via `staticmap`-Python-Package oder `mapbox-static-image`-Equivalent → Tile-Komposit als embedded `<image href="data:image/png;base64,...">` im SVG
  - Tiles werden gecacht in `backend/data/tile_cache/` (Tile-License: CartoDB CC BY 3.0 mit Attribution im Footer)
  - Fallback: bei Tile-Fetch-Fehler oder Offline-Test → einfacher hellgrauer Background, kein Crash
- Im `html_report.py` (Teaser) eingebunden via `{% include "visuals/risk_dashboard.svg.jinja2" %}` — voll sichtbar
- Im neuen Vollbericht-HTML (V.4) eingebunden — voll sichtbar (V.4 setzt das Template, V.2 stellt nur den SVG bereit)
- Smoke-Test mit Schulstraße-12-Daten ergibt rendered Teaser-PDF mit beiden Visuals

**Akzeptanz:**
- Beide Visuals matchen die Reference-SVGs visuell (Spot-Check)
- Schwellen-Logik aus Spec §4.1 und §4.2 implementiert
- Bei fehlenden Daten: Boxen mit „—", PSI-Hinweis „Sparse Data" wenn <10 Punkte
- Karte zeigt Basemap-Tiles oder sauberen Fallback; Attribution sichtbar in Footer
- Inline SVG funktioniert ohne JavaScript und ohne externe CSS

### Phase V.3 — Tier-2-Templates + Teaser-Wrapper

**Outputs:**
- 4 weitere Templates: `velocity_timeseries.svg.jinja2`, `soil_context_stack.svg.jinja2`, `correlation_radar.svg.jinja2`, `neighborhood_histogram.svg.jinja2`
- `backend/templates/visuals/_teaser_wrapper.svg.jinja2` — wrappt ein Sub-SVG mit `feGaussianBlur` Filter + Schloss-Icon-Overlay
- Im Teaser eingebunden: alle 6 Visuals; Tier-2 mit Wrapper, Tier-1 ohne
- Im Vollbericht eingebunden: alle 6 voll sichtbar (Premium, kein Wrapper)

**Akzeptanz:**
- Velocity-Zeitreihe zeigt Trendlinie aus linearer Regression, Korrelations-r im Footer
- Korrelations-Spinne normiert Achsen auf 0–5; bei fehlender Achse „n/a" statt Polygon-Punkt
- Bodenkontext-Stapel skaliert Schichthöhen proportional, Grundwasserlinie nur wenn Wert da
- Histogramm zeigt eigene-Adresse-Marker mit gestrichelter Linie
- Tier-2-Teaser im Free-Report zeigt Blur + Schloss-Overlay, Premium zeigt voll

### Phase V.4 — Vollbericht-Refactor: FPDF → Chrome-Headless HTML→PDF

**Hintergrund:** Aktueller `full_report.py` ist FPDF-basiert. Layout ist „abgrundtief hässlich" (User 2026-05-01). Magazin-Niveau-Typografie und das Cozy-Designsystem (Sentient/Geist Mono mit Kerning, polygon-clip-path-Pillen, polygon-corners auf Cards, inset green glow) sind in FPDF nur unter Schmerzen erreichbar. Refactor auf Chrome-Headless HTML→PDF nutzt den bestehenden `pdf_renderer.py`, deckt das Cozy-Designsystem 1:1 ab, und liefert vector-SVGs ohne PNG-Bridge.

**Outputs:**

1. **Neues HTML-Template-System:**
   - `backend/templates/full_report/base.html` — Document-Skeleton, `@page`-Regeln, Print-CSS-Includes
   - `backend/templates/full_report/cover.html` — Cover-Page (schwarz, GeoForensic-Logo, Adresse als Hero-Text, Bericht-Nr., Erstelldatum, QR-Code zur Provenance-URL)
   - `backend/templates/full_report/block_separator.html` — Trenn-Seite zwischen den 4 thematischen Blöcken
   - `backend/templates/full_report/section_*.html` — eine Datei pro Sektion (Bodenbewegung, Schwermetalle, Bergbau, Hochwasser, KOSTRA, SoilGrids, Nährstoffe, Geländeprofil, EU-Soil-Directive, Pestizide, Altlasten, Individuelle Einschätzung)
   - `backend/templates/full_report/data_sources.html` — Letzte Seite mit Provenance-Block, Datenquellen-Liste, Disclaimer
2. **CSS in `backend/static/css/full_report.css`:**
   - `@page { size: A4; margin: 18mm 14mm 22mm 14mm; }` — DIN A4 mit konsistenten Rändern
   - `@page :first { /* Cover hat keine Margin/Footer */ }`
   - Running-Headers/Footers via `@page { @bottom-center { content: "GeoForensic Vollbericht — Bericht-Nr. " counter(page) " von " counter(pages); } }`
   - Cozy-Designsystem: `--color-bg: #000`, `--color-accent: #22C55E`, `--color-border: #424242`
   - Typografie-Skala: H1 (Block), H2 (Sektion), H3 (Sub-Sektion), Body, Caption, Footnote — alle mit klar getrennten line-heights
   - Polygon-clip-path für Pillen und Card-Corners (Cozy-Standard)
   - Print-spezifisch: `page-break-before`, `widows`, `orphans`, `break-inside: avoid` auf Visuals und Tabellen
3. **Thematische 4-Block-Strukturierung:**
   - Block 1: Bodenrisiken aus Satellit/Wetter (EGMS, Hochwasser, KOSTRA)
   - Block 2: Untergrund & Topographie (Geländeprofil, Bergbau, Altlasten)
   - Block 3: Bodenchemie (Bodenqualität, Schwermetalle, Nährstoffe, Pestizide)
   - Block 4: Gesamt-Bewertung (EU Soil Directive, Individuelle Einschätzung)
   - Jeder Block bekommt eine Trenn-Seite mit Block-Headline + Kurz-Status (Ampel-Set)
4. **`full_report.py` Refactor:**
   - Alte FPDF-Logik wird gelöscht (nicht parallel halten — kein Backwards-Compat-Shim)
   - Neue Funktion `build_full_report_pdf(payload: dict) -> bytes` rendert via `pdf_renderer.render_html_to_pdf()`
   - QR-Code via `segno`-Package, eingebettet als Data-URI im HTML
   - Aufruf-Stelle in `routers/leads.py` bleibt (Signatur stabil)
5. **CMYK-Profile (optional, nice-to-have):**
   - Wenn Käufer drucken: `pikepdf` oder `pdf-color-profile` Post-Processing-Step nach dem PDF-Render, embedded ICC-Profile
   - Nicht must-have für Launch, aber Akzeptanz-Test schreibt das Profile-Embedding zumindest in der Pipeline-Pfad

**Akzeptanz:**
- Vollbericht hat sichtbare 4-Block-Struktur, Käufer kann thematisch navigieren
- Cover-Page wirkt professionell — Magazin-Niveau, kein Tabellen-Crash
- Typografie-Hierarchie ist konsistent (alle Block-Header gleich gestaltet, alle Sektion-Header eine Stufe darunter)
- Sentient + Geist Mono rendern ohne Font-Substitution-Warning
- Alle 6 Visuals als inline SVG eingebettet (nicht als PNG)
- Page-Footer auf jeder Seite außer Cover („GeoForensic Vollbericht / Bericht-Nr. xxx / Seite x von y")
- PDF-Größe < 1.5 MB inkl. der 6 Visuals und 2 Fonts
- Vollbericht-PDF in DIN A4, scharf bei 200% Zoom
- Smoke-Test gegen Live-Adresse mit allen 12 Sektionen rendert ohne Errors
- WeasyPrint-Fallback rendert ohne Crash (auch wenn Layout leicht abweicht — Akzeptanz: keine fatal errors, Inhalt vollständig)
- Ein bestehender FPDF-Vollbericht und der neue HTML-Vollbericht werden Side-by-Side für eine Adresse generiert und in `STATUS_2026-05-XX.md` als Vergleichs-Screenshots hinterlegt

**Wichtig:** Spec §3 (visuelles Vokabular der 6 Komponenten) ist weiterhin bindend. Cozy-Design-System gilt für den Premium-HTML-Wrapper, nicht für den Free-Bericht.

### Phase V.4.6 — Free-Bericht Layout-Polish (bodenbericht-Tailwind)

**Hintergrund:** Free-Bericht ist aktuell solide, aber Lock-Pille + Section-Trenner können konsistenter werden. Sub-Polish, kein Refactor.

**Was sich ändert:**
- **Lock-Pille:** einheitliches Design über alle 13 Locked-Cards
- **Section-Trenner:** klarer „IM VOLLBERICHT ENTHALTEN"-Strap zwischen Free-Sektionen und Locked-Cards
- **CTA-Polish:** der „Auf die Warteliste"-Block am Ende mit kleiner Vorschau der 6 Visualisierungen (verlinkt auf Demo)
- **Trust-Bar:** Datenquellen-Logos als kleine Badges am Anfang sichtbar (EGMS / SoilGrids / LUCAS / etc.)
- **Footer-Branding:** bodenbericht.de Logo + DSGVO-Note konsistent

**Outputs:**
- `html_report.py` Polish-Pass über bestehende Tailwind-Klassen
- Tailwind-Build wenn neue Klassen verwendet werden (siehe Phase B.3 Lessons-Learned: `tailwind-input.css` + npx tailwindcss)
- Smoke-Test gegen aktuellen Free-Bericht (5 Seiten) — neue Version sollte gleiche Seitenzahl behalten oder weniger

**Akzeptanz:**
- Free-Bericht wirkt freundlich/leicht/Käufer-fokussiert, klar als Lead-Magnet erkennbar
- Visuelle Konsistenz zur bodenbericht.de Landing-Page
- Conversion-Hebel deutlich sichtbar: was kostet Premium, was bekommt der Käufer mehr

**Wichtig:** Free-Bericht bleibt Tailwind-basiert, NICHT Cozy. Beide Reports haben dadurch eigene visuelle Identität.

### Phase V.4.7 — bodenbericht.de Landing-Polish

**Hintergrund:** User-Anforderung 2026-05-01: „wir wollen die landing page und die berichte so optisch schön wie möglich darstellen". V.4 + V.4.6 decken die PDFs ab. Die Landing-Seite selbst (`landing/index.html`) ist seit Phase B nicht visuell überarbeitet worden und hängt einen Schritt hinter dem neuen Visual-Niveau zurück.

**Was sich ändert:**
- **Hero-Refresh:** statt aktuellem Headline-Block ein Visual-Hero mit animierter Mini-Variante des Risiko-Dashboards (SVG aus V.2, statisch oder mit Subtle-Idle-Animation via CSS) als Eye-Catcher direkt over-the-fold
- **Visual-Showcase-Sektion:** eine eigene Sektion zwischen Hero und 16-Descriptor-USP-Block, die alle 6 Visualisierungen als statische Previews zeigt — „Das bekommen Sie im Vollbericht". Klick führt zur Demo (V.6) oder zur Stripe-Waitlist
- **Type-Hierarchie:** Konsistente Typografie-Skala (Tailwind-`text-*`-Klassen vereinheitlichen, aktuell mischt sich `text-lg`, `text-xl`, `text-2xl` ohne System)
- **Spacing-System:** durchgängige `space-y-*`/`gap-*`-Werte (8/12/16/24/32/48), aktuell ad-hoc-Margins
- **Trust-Bar in Hero:** Datenquellen-Logos (EGMS / Copernicus / SoilGrids / DWD KOSTRA / BfG) klein als Reihe direkt unter Hero-CTA
- **Mobile-Audit:** alle neuen Visual-Embedds auf Mobile (375px, 414px) testen, Stack-Layout statt Grid wo nötig
- **Performance-Check:** Lighthouse-Audit nach Polish — LCP < 2.5s, CLS < 0.1

**Outputs:**
- `landing/index.html` Polish-Pass mit den 5 Punkten oben
- Inline-SVG-Embeds der 6 Visuals (statisch, mit Beispieldaten) — wiederverwendet aus `backend/templates/visuals/*.svg.jinja2` durch Template-Pre-Render-Step (z.B. `landing/scripts/build_landing_visuals.py` rendert die SVGs einmalig mit Schulstraße-12-Daten und schreibt sie nach `landing/static/visuals/*.svg`)
- Tailwind-Build mit neuen Utility-Klassen falls nötig
- `landing/datenquellen.html` ggf. ergänzt um Logo-Liste der Trust-Bar

**Akzeptanz:**
- Hero-Visual ist über-the-fold sichtbar auf 1440px-Desktop und 375px-Mobile
- Visual-Showcase-Sektion zeigt alle 6 Komponenten korrekt (kein Layout-Bruch)
- Lighthouse Performance ≥ 90, Accessibility ≥ 95, Best-Practices ≥ 95, SEO ≥ 95
- Mobile-Render ohne horizontalen Scroll, alle CTAs erreichbar
- Side-by-Side-Screenshot Pre/Post in `STATUS_2026-05-XX.md` dokumentiert
- Visuelle Konsistenz zu Free-Bericht (V.4.6) — gleiche Tailwind-Klassen, gleiche Typografie

**Spielraum:** Cozy darf hier visuell mitsprechen, aber Landing bleibt **Tailwind**, nicht Cozy-Designsystem. Andernfalls bricht die Marken-Trennung bodenbericht.de (freundlich) vs. geoforensic.de (professionell).

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

### Phase V.7 — Documentation + Provenance Update + Visual-Regression-Tests

**Outputs:**
- `docs/DATA_PROVENANCE.md` ergänzt um neue Module (Burland, Pearson, geology, building_footprint)
- `CLAUDE.md` § Working-in-Production aktualisiert (Vollbericht jetzt HTML statt FPDF, Render-Pfad in Tabelle anpassen)
- `STATUS_<datum>.md` schreiben mit Side-by-Side-Vergleichen Pre/Post-Refactor
- **Visual-Regression-Test-Suite** unter `tests/visuals/`:
  - 3 Beispiel-Adressen: urban-dicht (Berlin), sparse (Schulstraße 12 Gaggenau), NL (Rotterdam)
  - Pro Adresse: Free-PDF, Vollbericht-PDF, Landing-Hero-Screenshot
  - Snapshot-Diff via `pytest-image-diff` (oder ähnlich), CI-blockend bei >5% Pixel-Diff
  - Refresh-Workflow: `pytest --update-snapshots` regeneriert Baseline
- **Sparse-Data-Gesamt-Verhalten:** Akzeptanz-Test schreibt vor — wenn weniger als 4 von 6 Visuals befüllbar sind, soll der Vollbericht eine kürzere Variante mit explizitem Hinweis rendern statt 6 Geister-Sektionen. Logik in `visual_payload.build_payload()` setzt Flag `low_data_mode: True`, Templates respektieren das

---

## 5. Reihenfolge mit Abhängigkeiten

```
V.0.1 Burland     ─┐
V.0.2 Pearson     ─┤── parallel ──┐
V.0.3 geology     ─┤              │
V.0.4 footprint   ─┘              │
                                  ↓
V.0.5 Payload-Builder ──→ V.1 Foundation ──→ V.2 Tier-1 ──→ V.3 Tier-2
                                                                   │
V.0.6 Provenance (additiv, parallel zu allem ab V.0.1)             │
                                                                   ↓
                                                      V.4 Vollbericht-Refactor (Chrome-Headless)
                                                                   │
                                                ┌──────────────────┼──────────────────┐
                                                ↓                  ↓                  ↓
                                           V.4.6 Free-Polish   V.4.7 Landing      V.5 Frontend-React
                                           (Tailwind)          (Tailwind)         (Cozy-Repo)
                                                                                      │
                                                                                  V.6 Frontpage-Demo
                                                                                      │
                                                                                  V.7 Docs + Visual-Regression-Tests
```

**Critical path:** V.0.1–V.0.5 müssen vor V.1. V.4 ist Voraussetzung für V.4.6 und V.4.7 nicht zwingend — die zwei Polish-Phasen können parallel zu V.4 laufen, weil sie eigene Render-Pfade haben (`html_report.py` und `landing/index.html`). V.5/V.6 (Cozy-Frontend) sind komplett parallel zu allem nach V.3, weil sie die Templates aus V.2/V.3 als Markup-Vorlage übernehmen aber in einem anderen Repo leben.

V.0.6 ist **additiv** und kann parallel zu V.0.1–V.0.4 laufen oder sogar nach V.1 nachgezogen werden — kein critical-path-Blocker.

V.4 ist der zeitlich teuerste Step (Refactor + komplettes neues HTML/CSS-System). Wenn das in einer Session nicht durchgeht, ist sauberer Sub-Phase-Schnitt:
- V.4a: HTML-Skelett + CSS-Print-Setup + Cover-Page
- V.4b: Block-Trennseiten + Sektion-Templates + 6 Visuals einbinden
- V.4c: Page-Footer + QR + Provenance-Seite + CMYK-Profil

---

## 6. Risiken und Stolperfallen

### 6.1 Chrome-Headless-Verfügbarkeit auf VPS
`pdf_renderer.py` nutzt Chrome-Headless seit April 2026 produktiv für den Teaser. Container hat Chromium drin. Sollte stabil sein. **Vorab-Check vor V.4:** `docker exec backend chromium --version` auf dem VPS, sicherstellen dass Version >= 120 für vollen `@page`-Support.

### 6.2 WeasyPrint-Fallback-Drift
WeasyPrint ist als Fallback im `pdf_renderer.py` drin, aber CSS-Paged-Media-Coverage ist enger. Risiko: V.4-CSS funktioniert in Chrome perfekt, in WeasyPrint mit Layout-Brüchen. **Mitigation:** Akzeptanz-Test in V.4 läuft beide Pfade durch. WeasyPrint-Output muss „inhaltlich vollständig" sein, Layout-Drift ist OK. Wenn WeasyPrint zu stark drifted, in V.4 als Risiko dokumentieren und WeasyPrint-Fallback nur als „Notfall-Render" deklarieren.

### 6.3 Font-Subsetting-Lizenz
Sentient + Geist Mono sind kommerzielle/freie Display-Fonts. Vor V.1: Lizenzen prüfen — ist Subsetting + Embedding erlaubt? (Geist Mono = OFL, ja. Sentient = Indian Type Foundry, free for commercial wenn nicht weiterverkauft, ja — aber Lizenz-Notiz im Repo ablegen.)

### 6.4 LoD2 Building-Footprint
Spec erwartet LoD2-Polygon — wir nehmen erstmal OSM Overpass als Stand-In. Das gibt für die meisten DE-Adressen ein Polygon, ist aber simpler als LoD2 (kein Höhenprofil, weniger detailreich). Cozy soll das wissen, könnte Reference-SVG entsprechend anpassen.

### 6.5 Schulstraße 12 Geocoding
`example_payload.json` hat Lat/Lon `48.80123, 8.32456` — vor V.0.5 mit Nominatim verifizieren, falls die Koords falsch sind, Daten neu berechnen. Sonst bricht der Demo-Sample.

### 6.6 Basemap-Tile-Lizenz und Performance
CartoDB Positron ist CC BY 3.0 (Attribution erforderlich). Stamen Toner ist CC BY 3.0. Tile-Fetch macht den Render-Pfad netz-abhängig — Tile-Cache in `backend/data/tile_cache/` ist Pflicht, sonst 500ms-Latenz pro Bericht. Fallback bei Tile-Fetch-Fehler: hellgrauer Background statt Crash.

### 6.7 ProofTrailAgents-Endpoint-Drift
Wir haben in der vorigen Session festgestellt, dass viele Behörden-Endpoints aus ProofTrailAgents tot sind (PDOK Bodemloket, LANUV NRW, LUBW). Bei V.0.3 (geology aus PTA) wird wahrscheinlich der BGR GUEK200-Endpoint auch geprüft und ggf. korrigiert werden müssen.

### 6.8 PDF-Größe nach Refactor
Mit 2 inline woff2-Fonts (60 KB), 6 inline SVGs mit Basemap-Tile-Datas (300 KB total worst-case), und 12 Sektionen mit Tabellen kann die PDF-Größe explodieren. Akzeptanz-Limit: 1.5 MB. Mitigation: Tile-PNG-Komprimierung (`Pillow` mit `optimize=True`), SVG-Minifizierung (`scour`-Package).

---

## 7. Was nach diesem Sprint offen bleibt

- **LoD2-Building-Footprints für DE-Bundesländer** mit eigenen Diensten (NRW, BW, BY, SN — nicht alle haben Public-WFS)
- **LGRB BW Hydrogeologie** für Grundwasser-Achse in der Korrelations-Spinne — andere Bundesländer haben eigene Quellen
- **NL-Pendant für die Visuals** — alle 6 müssen NL-i18n bekommen wenn wir den NL-Markt bedienen (eigener Sprint analog Phase C)
- **Echte Slippy-Map** auf der Web-Seite (MapLibre + EGMS-Vector-Tiles) als Folge-Ticket. In V.2 ist die Karte Server-rendered Static-Composit, was für PDF-Use-Case ausreicht aber im Web limitiert.

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

**Spec-Abweichung dokumentiert:** Spec §2 sagt „Chrome Headless rendert HTML mit eingebetteten SVGs" — das gilt jetzt für **beide** Reports. Die FPDF-Variante in `full_report.py` ist obsolet und wird in V.4 gelöscht.
