# GeoForensic App

Two-product repo for address-based ground motion + soil screening.

**Repo:** https://github.com/8endit/geoforensic-app
**Operational truth:** `docs/TEAM_HANDBOOK.md` (server, deploys, DNS, monitoring).

## Two products in one repo

| Product | Domain | Role | Report variant |
|---|---|---|---|
| **bodenbericht.de** | **live** | Free lead-magnet landing + quiz funnel | **Teaser PDF** — short, deliberately limited |
| **geoforensic.de** | planned | Paid product, Groundsure-style depth | **Full PDF** — all engine output (not wired yet) |

Routing happens via the lead `source` field in
`backend/app/routers/leads.py` — `TEASER_SOURCES = {"quiz", "landing",
"premium-waitlist"}`. Anything else is reserved for the future paid/full
flow and currently falls back to the teaser with a log warning.

## Architecture

```
geoforensic-app/
├── backend/          # FastAPI + PostgreSQL/PostGIS (deployed)
│   ├── app/
│   │   ├── main.py               # FastAPI app, CORS, lifespan, mounts landing/
│   │   ├── config.py             # pydantic-settings (.env)
│   │   ├── database.py           # SQLAlchemy async
│   │   ├── models.py             # User, Lead, Report, Payment (ORM)
│   │   ├── schemas.py            # Pydantic request/response
│   │   ├── auth.py               # JWT + bcrypt
│   │   ├── dependencies.py       # get_current_user, get_db
│   │   ├── html_report.py        # TEASER report (bodenbericht.de) - polished V.4.6
│   │   ├── full_report.py        # FULL report (geoforensic.de) - HTML→Chrome since V.4 (2026-05)
│   │   ├── visual_payload.py     # Aggregator → data_contract.json (V.0.5)
│   │   ├── visual_renderer.py    # Jinja-SVG renderer for the 6 visuals (V.1)
│   │   ├── basemap.py            # CartoDB Positron tile composite (V.2.3)
│   │   ├── chart_helpers.py      # Render-context builders for 4 Tier-2 charts (V.3)
│   │   ├── burland_classifier.py # Burland 1995 1-6 + A-E grade (V.0.1)
│   │   ├── correlations.py       # Pearson r EGMS x precipitation (V.0.2)
│   │   ├── geology.py            # BGR GÜK250 ArcGIS REST (V.0.3)
│   │   ├── building_footprint.py # OSM Overpass building lookup (V.0.4)
│   │   ├── pdf_renderer.py       # Chrome-headless HTML -> PDF (WeasyPrint fallback)
│   │   ├── soil_data.py          # SoilGrids + LUCAS point queries
│   │   ├── flood_data.py         # BfG HWRM Hochwasser WMS (DE)
│   │   ├── mining_nrw.py         # NRW Bergbauberechtigungen WMS
│   │   ├── kostra_data.py        # DWD KOSTRA-2020 Starkregen-Raster
│   │   ├── geocode_cache.py      # Redis-backed Nominatim cache (30d TTL)
│   │   ├── email_service.py      # Brevo SMTP, HTML+plaintext, is_teaser flag
│   │   └── routers/
│   │       ├── auth.py           # register, login, me
│   │       ├── leads.py          # POST /api/leads (quiz + landing funnel)
│   │       ├── reports.py        # preview, create, list, detail, pdf, csv
│   │       ├── payments.py       # Stripe checkout + webhook (not wired live)
│   │       ├── admin.py          # /api/_admin/{stats,leads,activity}
│   │       └── health.py
│   └── Dockerfile, requirements.txt
├── landing/                # Static HTML served by FastAPI mount (bodenbericht.de)
│   ├── index.html          # Hero + inline form + testimonials + FAQ + waitlist
│   ├── quiz.html           # Multi-step quiz → /api/leads
│   ├── admin.html          # Lead dashboard + CSV export
│   ├── impressum.html, datenschutz.html, widerruf.html, datenquellen.html
│   ├── muster-bericht.html # Sample report preview
│   └── images/, fonts/, klaro/ (DSGVO consent)
└── docker-compose.yml
```

## Design System (by Cozy) — for geoforensic.de only

The Next.js + R3F frontend lives in its **own repo**:
[github.com/8endit/cozy-frontend](https://github.com/8endit/cozy-frontend),
checkout local at `C:\dev\cozy-frontend\cozy-frontend\`. It is **not** a
subdir of this repo. Reason: backend and Cozy-UI deploy at different
velocities and the design needs its own iteration cycle.

This system was designed for the paid product (`geoforensic.de`) and the
Next.js frontend. **bodenbericht.de does NOT follow it** — bodenbericht uses
its own lighter Tailwind setup under `landing/` with a calmer palette.

Must be followed for ALL new pages on geoforensic.de:
- **Background:** `#000000` (pure black)
- **Primary accent:** `#22C55E` (lime green) — buttons, links, indicators
- **Border:** `#424242`
- **Font display:** Sentient (woff, extralight + light italic)
- **Font mono:** Geist Mono (all UI text, nav, forms, data)
- **Buttons:** Polygon clip-path corners (16px), diagonal corner decoration lines, inset green glow (`box-shadow: inset 0 0 54px`)
- **Pills:** Polygon clip-path (6px), green dot indicator with glow
- **Text:** Always `uppercase` on nav/buttons, `font-mono` for UI
- **Opacity scale:** foreground/40, /60, /70, /80 for hierarchy
- **Inputs:** `bg-transparent border border-border`, focus → `border-primary`
- **Cards:** `bg-black/40 border border-border`

## Current State (2026-04-30)

### Deployment (live)

- **Host:** Contabo VPS `185.218.124.158` (`vmd195593`), `/opt/bodenbericht`
- **TLS:** Caddy (80/443) → FastAPI (8000 intern) — Let's Encrypt
- **DB:** PostGIS 16-3.4 in Docker, internal only
- **Domain:** `https://bodenbericht.de` (A + A www)
- **Deploy:** `ssh root@…` + `git pull` (landing HTML hot-reloads via bind-mount, backend needs `docker compose build backend && up -d`)
- **Runbook:** `docs/TEAM_HANDBOOK.md`

### Working in production

- Landing + quiz funnel + lead capture → background geocode + EGMS query + PDF + Brevo mail
- Teaser PDF via `backend/app/html_report.py` (Chrome-headless rendered) — 13 Locked-Cards + Trust-Bar mit 8 Datenquellen + Lock-Pille „Vollbericht freischalten" + CTA mit 6-Tile Mini-Vorschau (V.4.6 polish)
- Vollbericht PDF via `backend/app/full_report.py` (Chrome-headless HTML→PDF, V.4 refactor) — Cover + 4 thematische Blöcke + 12 Sektionen mit allen 6 Visuals als inline SVG + Provenance/Datenquellen-Seite mit QR. Sentient + Geist Mono inline embedded. ~440 KB pro Bericht.
- Landing-Page narrativ um die 6 Visuals herum redesigned (V.4.7): Hero mit Risiko-Dashboard rechts, Problem-Sektion mit alternierenden Image-Text-Rows, How-It-Works mit Berlin-Karte, Benefits mit Korrelations-Spinne, Premium-Teaser mit 6-Tile-Mini-Grid
- `source`-based routing hook in `leads.py` (teaser vs. full report) — country-gated für DE/NL/AT/CH
- Admin dashboard `landing/admin.html` with leads, stats, CSV export, TEASER/VOLL badge
- Legal pages (Impressum, Datenschutz, Widerruf, Datenquellen) + Musterbericht
- Analytics: GTM `GTM-KFG5W96X`, GA4 `G-N9H86S1P8V`, PostHog EU — all DSGVO-gated via Klaro
- Brevo SMTP + branded HTML mail (inline logo, DKIM via `geoforensic.de`)
- Waitlist + Early-Bird teaser for future paid product

### Vollbericht-Pipeline (scharfgeschaltet, 12 Sektionen)

Aktive Datensätze und Module nach Phase A+B (April 2026):

| Modul | Datenquelle | Lizenz |
|---|---|---|
| EGMS InSAR (PostGIS) | Copernicus EGMS L3, 7,9 Mio Punkte DE/NL/AT/CH | CC BY 4.0 |
| `soil_data.py` SoilGrids | ISRIC SoilGrids 250m, 6 Variablen | CC BY 4.0 |
| `soil_data.py` LUCAS | JRC ESDAC, Schwermetalle + Nährstoffe DE | EU Open Data |
| `soil_data.py` CORINE 2018 | Copernicus EEA CLC2018 v2020_20u1, DE+NL Clip | Copernicus FFO |
| `soil_data.py` HRL Imperv. | Copernicus HRL 20m, DE-Bounds | Copernicus FFO |
| `soil_data.py` WRB Soil | SoilGrids MostProbable 1-29, AWC-Lookup | CC BY 4.0 |
| `pesticides_data.py` | LUCAS Pesticides 2018 NUTS2 (118 actives) + Eurostat NUTS-2021 | EU Open Data |
| `slope_data.py` | OpenTopoData (SRTM 1-arcsec) primary + Open-Elevation fallback | Public Domain / MIT |
| `soil_directive.py` | EU 2025/2360, 16 Descriptoren mit BBodSchV-Schwellen DE / Circulaire bodemsanering NL | gesetzliche Grundlage |
| `rfactor_data.py` | **ESDAC Panagos 2015 LIVE** (429 MB-Raster auf VPS seit 1.5.2026, source=esdac-2015 verifiziert) | ESDAC ToS |
| `altlasten_data.py` | NL: PDOK Bodemloket WBB-Lokationen / DE: CORINE-Land-Use-Proxy | CC-BY 4.0 / Copernicus |
| `flood_data.py` | BfG HWRM-RL 3 Szenarien, vom VPS verifiziert | DL-DE/Zero-2.0 |
| `mining_nrw.py` | Bezirksregierung Arnsberg WMS (NRW only) | dl-de/by-2.0 |
| `kostra_data.py` | DWD KOSTRA-DWD-2020 — **alle 6 buyer-relevanten Slots LIVE** seit 2.5.2026 (D60_T1a/T10a/T100a + D1440_T1a/T10a/T100a, rasterized aus GIS_*.zip Shapefiles via `scripts/download_kostra.py --ensure-default-set`) | GeoNutzV |

Country-Routing in jedem Modul:
- DE → BBodSchV-Schwellen, LUCAS-Lookup aktiv, lat-linear-DE R-Faktor, CORINE-Proxy für Altlasten
- NL → Circulaire-bodemsanering-Schwellen, **kein** LUCAS (Country-Gate, nicht 200km-Brandenburg-IDW), NL-Konstante R-Faktor, PDOK-Bodemloket echtes Kataster
- AT/CH → BBodSchV als konservativer Default, eigene R-Faktor-Konstanten, Altlasten nicht integriert

Vollbericht-Sektionen (12, FPDF-basiert, ~165 KB):
1 Bodenbewegung · 2 Schwermetalle · 3 Bergbau · 4 Hochwasser · 5 KOSTRA Starkregen · 6 Bodenqualität (SoilGrids) · 7 Nährstoffe · 8 Geländeprofil · 9 EU Soil Directive 16 Descriptoren · 10 Pestizide · 11 Altlasten · 12 Individuelle Einschätzung

Datenquellen-Provenance: `docs/DATA_PROVENANCE.md` ist die einzige verbindliche Wahrheit pro Datenpunkt.

### Honest gaps (not working / half-working)

- **Vollbericht-Pipeline scharfgeschaltet, aber nicht customer-facing** — `full_report.py` ist seit 27.4. an den Lead-Flow angebunden (`source != TEASER_SOURCES` → Vollbericht). Quiz und Landing emittieren aber weiterhin nur Teaser-Sources. Triggerbar derzeit nur per direktem `POST /api/leads`.
- ~~**KOSTRA-Raster teilweise da**~~ — **erledigt 2.5.2026**: alle 6 buyer-relevanten Slots (60min × T1/T10/T100, 24h × T1/T10/T100) sind live. Quelle: GIS_KOSTRA-DWD-2020_D00060.zip + D01440.zip Shapefiles (manuell hochgeladen, weil DWD CDC `/asc/` nur die wertlose StatRR-Variante ohne CRS hostet) — Rasterisierung via `scripts/download_kostra.py --ensure-default-set` mit ogr2ogr-Reproject auf EPSG:4326 + gdal_rasterize HN_<NNN>A_-Spalten. Berlin-Werte: 14.8 / 29.9 / 48.9 mm (60min) und 30.9 / 62.7 / 102.6 mm (24h). Längere Dauerstufen (D360/D720/D2880) sind nicht in KOSTRA_SLOTS definiert und auch nicht angefragt.
- ~~**ESDAC R-Faktor-Raster fehlt**~~ — **erledigt 1.5.2026**, 429 MB-Raster auf VPS unter `/opt/bodenbericht/rasters/esdac_rfactor_eu_1km.tif`, `rfactor_data.py` liest mit `source=esdac-2015`.
- **Open-Elevation flaky** — primärer Slope-Lookup geht über OpenTopoData (1000 req/day cap), Open-Elevation als Fallback antwortet aktuell mit 504. Phase C: lokale SRTM-Tile-Cache.
- **Altlasten DE = nur CORINE-Proxy** — adress-genaue Altlasten-Daten in DE sind nach INSPIRE Art 13(1)(f) personenbezogen geschützt (LUBW ALTIS / LANUV FIS AlBo). Modul liefert Land-Use-Indikator + bietet Behörden-Vermittlung (`altlasten@geoforensic.de`) als zukünftiges Add-On. Kein Open-Data-Konter zu docestate.com möglich.
- **Stripe / paid flow** — code exists in `routers/payments.py`, not active on the domain
- **User accounts** — register/login routes work, but no live surface (bodenbericht is lead-only)
- ~~**CORINE land-use raster** — file on disk is corrupt~~ — **erledigt**: `corine_2018_clc_100m_de_nl.tif` (11 MB) liegt seit 30.4.2026 auf VPS, Live-Test 2.5.2026 liefert für Stuttgart `code=111, label="Durchgängig städtische Prägung", source=corine-2018`. Code in `soil_data.py` `query_corine()` aktiv genutzt.
- **HRL imperviousness + AWC water capacity** — rasters are DE-bounds only, NL addresses return NODATA
- **Map in PDF** — Teaser hat Static-Map auf Seite 1; Cozy designt Vollbericht-Karten separat
- **NL-language report** — PDF is German only; NL is supposed to be primary market for the paid product
- ~~**Sentry**~~ — **scharfgeschaltet 2.5.2026**: DSN für EU-Region (`ingest.de.sentry.io`), DSGVO-konform mit `send_default_pii=False` + Email-Scrubber. DSN aus Repo-Root `.env` (NICHT `backend/.env`!), siehe `memory/bodenbericht_sentry_config.md`. Datenschutzerklärung um Sentry-Sektion ergänzt.
- **Better Stack Uptime** — not yet scheduled
- **SSH password login** — still enabled on the server (key-only hardening is TODO in handbook §2.2)
- **BBSR / GFZ Lizenz-Klärung offen** — Mail-Vorlagen liegen in `docs/MAIL_BBSR_LIZENZ.md` und `docs/MAIL_GFZ_ERDBEBEN.md`, noch nicht rausgeschickt.

### Near-term next steps

1. **YFxEU → main mergen** und Backend neu bauen (Redis-Service kommt neu hinzu)
2. BfG-Layer-Namen vom VPS aus per `curl` verifizieren
3. KOSTRA-Raster nach `/opt/bodenbericht/rasters/kostra_dwd_2020/` hochladen
4. BBSR + GFZ-Lizenzanfragen rausschicken
5. Sentry-DSN scharfschalten + Test-Crash
6. SSH-Passwort-Login abschalten
7. **Dann** Cozy-Teaser-Design-Pass + paid-flow customer-facing machen (Stripe, Quiz-Source-Routing, NL-Variante)

## Business Context

### What this product IS and IS NOT
- IS: an automated **Standortauskunft** / **Bodenbewegungsscreening** (data screening)
- IS NOT: a **Gutachten** (expert assessment). NEVER use the word "Gutachten" anywhere in the product, UI, or marketing. This has legal implications — it implies a certified expert did a physical site inspection and triggers full professional liability under German law.
- The PDF disclaimer in `backend/app/html_report.py` (teaser) and `backend/app/full_report.py` (full, not live yet) is legally required. Do not weaken or remove it.

### Target Markets (in order)
1. **Netherlands (primary, launching first):** Since April 1, 2026, every Dutch property valuation (taxatierapport) must include a foundation risk assessment (A-E label from KCAF/FunderMaps). Buyers who receive label C/D/E want to understand what that means — our report explains the satellite data behind the label with time series, maps, and trend analysis. We are the "second opinion" / "deep dive" next to the mandatory thin label.
2. **Germany (2027-2028):** EU Soil Monitoring Directive 2025/2360 requires transposition by ~Dec 2028. Property buyers will have a right to soil data. Germany currently has zero equivalent to the UK/NL property risk report market. We will be first-movers when the regulation hits.

### Competitors
- **FunderConsult (NL):** EUR 7.95/address, A-E risk label from FunderMaps database. Already includes InSAR data from SkyGeo for 40% of NL, but the buyer only sees a black-box label, NOT the raw velocity data, time series, or maps. Our report shows what theirs hides.
- **Groundsure (UK):** Market leader, sold for GBP 170M in 2021. Uses SatSense InSAR data. Reports from GBP 47. Not active in DE/NL.
- **France-ERP (FR):** EUR 9.99/report alongside free government data (georisques.gouv.fr). Proves the model: free government data + paid commercial report coexist.
- **Germany — NICHT leer.** Frühere Doc-Behauptung "no competitor exists" war ein Recherche-blinder-Fleck. Aktueller Stand (siehe `docs/MARKET_REALITY_DE_2026.md` für Details):
  - **BBSR GIS-ImmoRisk** — gratis, staatlich, deckt Hitze/Erdbeben/Waldbrand/Hagel/Sturm/Starkregen pro Adresse ab. Killer für ein "wir machen Naturgefahren"-Modul.
  - **K.A.R.L.® TAXO** (Köln.Assekuranz/ERGO via on-geo) — B2B Klimarisiko + EU-Taxonomie-Compliance, CMIP6-Projektionen.
  - **on-geo Lora** — B2B Beleihungswert, sitzt in 95 % der DE-Banken.
  - **EnviroTrust** — B2B Climate-Risk-Plattform.
  - **docestate.com** — B2C Altlastenkataster pro Grundstück, ~30–100 EUR.
  - Was niemand kombiniert: **gemessene InSAR-Bodenbewegung mit Zeitreihen + Käufer-PDF + EU-Soil-Directive-Compliance**. Das ist unser einziger echter Moat.
  - **Pflichtversicherung Elementar** ist im Koalitionsvertrag 2025 + Bundesrats-Vorstoß + Linke-Antrag 16.04.2026 — noch nicht beschlossen. Falls Opt-out-Modell kommt: ~50 Versicherer brauchen adressgenaue Risikodaten → B2B-API-Sog.
  - **Strategieentscheidung Avista-Parität vs. Soil-Act/InSAR-Pivot ist offen** — bis zur Entscheidung kein neues Risikomodul anfangen.
  - Baugrundgutachten (EUR 849–2500, mit Bohrung) bleiben das einzige B2C-Pendant ohne Wettbewerb in der "Desk-Screening"-Nische.

### Pricing (NOT finalized — needs market validation)
- Current config: `STRIPE_REPORT_PRICE_CENTS=19900` (EUR 199) — likely too high for NL market
- Target NL: EUR 19-39 per report (between FunderConsult 7.95 and QuickScan 350+)
- Target DE: EUR 49-99 per report (kein direkter B2C-Desk-Screening-Wettbewerb in der Nische; B2B-Markt aber durch on-geo/K.A.R.L. besetzt)
- Free preview (ampel + point count, no auth needed) — this is the lead magnet
- Discussed but NOT implemented: first 100 free, promo codes, tiered pricing

### Data Sources & Licensing
- **EGMS (European Ground Motion Service):** Copernicus program, CC BY 4.0. Commercially usable. MUST include attribution: "Generated using European Union's Copernicus Land Monitoring Service information" — already in pdf_generator.py and report_data.
- **BGR BBD (Bodenbewegungsdienst Deutschland):** License NOT yet confirmed. Likely dl-de/by-2.0 (commercial OK). Pending email to BBD@bgr.de.
- **bodemdalingskaart.nl:** CC BY-SA 4.0. CAUTION: the SA (ShareAlike) copyleft means derivative works must use the same license. Do NOT use this data if it would force our reports to be open-licensed. Stick with EGMS (CC BY 4.0, no copyleft) as primary source.

#### Datendichte-Hinweis
Je dichter das Messpunkte-Netz pro Adresse, desto präziser lässt sich der
Bericht rechnen — mittlere Geschwindigkeit, Streuung, Trendklassifikation und
GeoScore werden statistisch belastbarer je mehr Punkte im Untersuchungsradius
liegen. Grobe Referenzwerte für ein 500 m-Umfeld in einer deutschen
Wohnsiedlung:

| Quelle | typisch Punkte / 500 m | Messzeitraum | NL abgedeckt? |
|---|---|---|---|
| EGMS | 50 – 80 | 2019 – 2023 | ja |
| BGR BBD | 80 – 120 | 2015 – 2024 | nein |

Unsere aktuelle Wahl (EGMS als einzige Quelle) ist ein bewusster Kompromiss
aus Lizenz-Sicherheit, EU-Abdeckung (NL ist Markt #1) und Datendichte. Für
deutsche Adressen bedeutet sie ca. 30–40 % weniger Messpunkte als der
BGR-Datensatz. Hybrid-Integration (EGMS-Basis + BGR BBD additiv für
DE-Adressen) steht auf der Roadmap für die geoforensic.de-Vollversion — dafür
muss die BGR-Lizenz vorher geklärt sein.

### Legal Requirements
- **Germany:** Standard Gewerbeanmeldung, no special license needed. Get Berufshaftpflichtversicherung (~EUR 150/year). AGB with disclaimer required for B2C.
- **Netherlands:** No Dutch entity needed (EU Services Directive). Register for OSS (One-Stop Shop) VAT when NL B2C revenue exceeds EUR 10k/year.
- **Both markets:** Impressum, AGB, Widerrufsbelehrung (with digital content exception), DSGVO privacy policy.

### Key Technical Decisions Informed by Business
- `countrycodes: "de,nl,at,ch"` in Nominatim — NL is a target market, not just DE
- The product must work for Dutch addresses (NL geocoding, NL EGMS data)
- PDF language is currently German — will need NL/EN versions later
- The `egms_points.country` field exists for multi-country data separation

## API Endpoints

See `docs/API.md` for full spec. Key routes live today:
- `POST /api/leads` — **main entry point**: quiz + landing form → teaser PDF + mail
- `POST /api/reports/preview` — free, rate-limited (10/hr), returns ampel
- `POST /api/reports/create` — auth required, full pipeline (not surfaced on live landing)
- `POST /api/payments/checkout` — Stripe session (code exists, not wired)
- `GET /api/reports/:id/pdf` — paid report download
- `GET /api/_admin/stats`, `/leads`, `/activity` — admin dashboard (token-gated)

## Ampel Classification

| Ampel | Velocity | Meaning |
|-------|----------|---------|
| grün  | < 2 mm/a | Unauffällig |
| gelb  | 2-5 mm/a | Auffällig, beobachten |
| rot   | > 5 mm/a | Signifikant, Gutachter hinzuziehen |

## Related Repos

- **geoforensic-karte**: Interactive map dashboard (170k points, GitHub Pages) — https://github.com/8endit/geoforensic-karte
- **ProofTrailAgents**: CLI + GitHub Actions for generating full PDF reports — https://github.com/8endit/ProofTrailAgents

## External References

- **EGMS**: EU InSAR data — https://egms.land.copernicus.eu/
- **BGR BBD**: German ground motion service — https://bodenbewegungsdienst.bgr.de/
- **KCAF/FunderMaps**: NL foundation risk database — https://www.kcaf.nl/fundermaps/
- **FunderConsult**: NL commercial reports — https://funderconsult.com/
- **bodemdalingskaart.nl**: NL subsidence map (SkyGeo) — https://bodemdalingskaart.nl/

## Task Docs for Cursor

- `docs/TEAM_HANDBOOK.md` — operational truth (SSH, deploy, DNS, monitoring)
- `docs/DATA_INVENTORY_AUDIT.md` — which rasters are nutzbar (CORINE kaputt, HRL/AWC DE-only)
- `docs/CURSOR_BACKEND_PIPELINE.md` — DONE: mock→real pipeline migration
- `docs/CURSOR_EGMS_DATA_ANALYSIS.md` — DONE: data density confirmed (79 pts/500m urban)
- `docs/EGMS_DATA_REPORT.md` — DONE: full analysis results
- `docs/CURSOR_UX_SECURITY_AUDIT.md` — security + UX fixes (prioritized list)
- `docs/CURSOR_LANDING_POLISH.md`, `CURSOR_LANDING_SPRINT2.md`, `CURSOR_LANDING_PREMIUM_TEASER.md` — landing iterations (shipped)
- `docs/CURSOR_TEASER_VS_FULL_REPORT.md` — **DONE in-tree**: source-based routing for teaser vs. full report
- `docs/PLAN_GEOFORENSIC_DE.md` — geoforensic.de paid-flow plan (Phasen, Märkte, Pricing-Thesen)
- `docs/MARKET_REALITY_DE_2026.md` — DE-Wettbewerbsrecherche (BBSR/K.A.R.L./on-geo/EnviroTrust/docestate), Strategie-Entscheidung Option B
- `docs/DATA_SOURCES_VERIFIED.md` — Layer-Katalog mit Verifizierungs-Stand (BfG, NRW, KOSTRA, Radon, Erdbeben)
- `docs/SPRINT_S1_DATA_INGEST.md` — Server-Upload-Patterns + Sprint-Reihenfolge
- `docs/MAIL_BBSR_LIZENZ.md`, `docs/MAIL_GFZ_ERDBEBEN.md` — Mail-Vorlagen, noch zu versenden
- `docs/STATUS_2026-04-29.md` — letzter Tagesstand (Konsolidierung von zwei verstreuten Branches)
