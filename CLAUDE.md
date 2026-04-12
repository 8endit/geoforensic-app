# GeoForensic App

SaaS product: address-based ground motion screening reports for properties in Germany and the Netherlands.
**Repo:** https://github.com/8endit/geoforensic-app

## Architecture

```
geoforensic-app/
├── backend/          # FastAPI + PostgreSQL
│   ├── app/
│   │   ├── main.py           # FastAPI app, CORS, lifespan
│   │   ├── config.py         # pydantic-settings (.env)
│   │   ├── database.py       # SQLAlchemy async
│   │   ├── models.py         # User, Report, Payment (ORM)
│   │   ├── schemas.py        # Pydantic request/response
│   │   ├── auth.py           # JWT + bcrypt
│   │   ├── dependencies.py   # get_current_user, get_db
│   │   └── routers/
│   │       ├── auth.py       # register, login, me
│   │       ├── reports.py    # preview, create, list, detail, pdf, csv
│   │       ├── payments.py   # Stripe checkout + webhook
│   │       └── health.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/geoforensic_webcode/   # Next.js 15 + React 19
│   ├── app/
│   │   ├── page.tsx          # Landing (Hero + PropertyForm)
│   │   ├── layout.tsx        # Geist Mono, lang=de, AuthProvider
│   │   ├── dashboard/        # Protected report list
│   │   ├── login/            # Sign in
│   │   ├── register/         # Sign up (with company/gutachter fields)
│   │   └── reports/[id]/     # Report detail + PDF/CSV download
│   ├── components/
│   │   ├── hero.tsx          # 3D particle hero (R3F)
│   │   ├── property-form.tsx # Address input → preview → report creation
│   │   ├── preview-result.tsx # Ampel badge + point count
│   │   ├── header.tsx        # Nav with auth-aware links
│   │   ├── mobile-menu.tsx   # Radix dialog, auth-aware
│   │   ├── gl/               # WebGL particle system (R3F + custom shaders)
│   │   └── ui/button.tsx     # Polygon-clipped button with glow
│   └── lib/
│       ├── api.ts            # Typed API client (fetchApi wrapper)
│       └── auth-context.tsx  # JWT in localStorage, AuthProvider
└── docker-compose.yml        # db + backend + frontend
```

## Design System (by Cozy)

Must be followed for ALL new pages:
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

## Current State (2026-04-12)

### Working
- Full auth flow (register, login, JWT, protected routes)
- Report CRUD (create, list, detail)
- Preview endpoint (free, rate-limited 10/hr) — real Nominatim geocoding
- Stripe checkout flow (mock mode when no key)
- PDF/CSV download with auth token (fetch+blob)
- 3D particle hero with DOF
- Mobile-responsive header + menu
- Real Nominatim geocoding (replaces old `_mock_geocode`)
- Real analysis pipeline (`_run_report_pipeline`) — queries PostGIS, weighted velocity, histogram
- Real PDF generation (WeasyPrint, lazy-import for Windows compat)
- PostGIS `egms_points` + `egms_timeseries` tables + GIST index + Alembic migration
- Docker Compose with `postgis/postgis:16-3.4`

### NOT Working / Blocked
- **`egms_points` table is EMPTY** — no EGMS data imported yet. Every report returns "0 points, green".
- PDF on Windows requires native GTK/Pango libs (works in Docker)
- No map visualization in PDF (just data table)

### Next Steps
1. ~~Download EGMS data + build import script~~ — DONE, see `docs/EGMS_DATA_REPORT.md`
2. ~~Verify data density~~ — DONE: 79 pts/500m Rotterdam, 77 pts/500m Essen. Urban = solid.
3. **NOW: UX & Security fixes** — see `docs/CURSOR_UX_SECURITY_AUDIT.md`
4. **THEN: Import EGMS archive data into PostGIS** — script ready at `backend/scripts/import_egms.py`, Copernicus credentials in `backend/.env`
5. Add map visualization to PDF (Leaflet static image or matplotlib)
6. Promo code system + free tier (first 100 reports)
7. Deploy: Hetzner Cloud CX22 (backend + PostGIS) + Vercel (frontend)

## Business Context

### What this product IS and IS NOT
- IS: an automated **Standortauskunft** / **Bodenbewegungsscreening** (data screening)
- IS NOT: a **Gutachten** (expert assessment). NEVER use the word "Gutachten" anywhere in the product, UI, or marketing. This has legal implications — it implies a certified expert did a physical site inspection and triggers full professional liability under German law.
- The PDF disclaimer in `pdf_generator.py` is legally required. Do not weaken or remove it.

### Target Markets (in order)
1. **Netherlands (primary, launching first):** Since April 1, 2026, every Dutch property valuation (taxatierapport) must include a foundation risk assessment (A-E label from KCAF/FunderMaps). Buyers who receive label C/D/E want to understand what that means — our report explains the satellite data behind the label with time series, maps, and trend analysis. We are the "second opinion" / "deep dive" next to the mandatory thin label.
2. **Germany (2027-2028):** EU Soil Monitoring Directive 2025/2360 requires transposition by ~Dec 2028. Property buyers will have a right to soil data. Germany currently has zero equivalent to the UK/NL property risk report market. We will be first-movers when the regulation hits.

### Competitors
- **FunderConsult (NL):** EUR 7.95/address, A-E risk label from FunderMaps database. Already includes InSAR data from SkyGeo for 40% of NL, but the buyer only sees a black-box label, NOT the raw velocity data, time series, or maps. Our report shows what theirs hides.
- **Groundsure (UK):** Market leader, sold for GBP 170M in 2021. Uses SatSense InSAR data. Reports from GBP 47. Not active in DE/NL.
- **France-ERP (FR):** EUR 9.99/report alongside free government data (georisques.gouv.fr). Proves the model: free government data + paid commercial report coexist.
- **Germany:** No competitor exists. Baugrundgutachten cost EUR 849-2500 and require physical boring. We are the desk-based screening alternative.

### Pricing (NOT finalized — needs market validation)
- Current config: `STRIPE_REPORT_PRICE_CENTS=19900` (EUR 199) — likely too high for NL market
- Target NL: EUR 19-39 per report (between FunderConsult 7.95 and QuickScan 350+)
- Target DE: EUR 49-99 per report (no competitor, higher willingness to pay)
- Free preview (ampel + point count, no auth needed) — this is the lead magnet
- Discussed but NOT implemented: first 100 free, promo codes, tiered pricing

### Data Sources & Licensing
- **EGMS (European Ground Motion Service):** Copernicus program, CC BY 4.0. Commercially usable. MUST include attribution: "Generated using European Union's Copernicus Land Monitoring Service information" — already in pdf_generator.py and report_data.
- **BGR BBD (Bodenbewegungsdienst Deutschland):** License NOT yet confirmed. Likely dl-de/by-2.0 (commercial OK). Pending email to BBD@bgr.de.
- **bodemdalingskaart.nl:** CC BY-SA 4.0. CAUTION: the SA (ShareAlike) copyleft means derivative works must use the same license. Do NOT use this data if it would force our reports to be open-licensed. Stick with EGMS (CC BY 4.0, no copyleft) as primary source.

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

See `docs/API.md` for full spec. Key routes:
- `POST /api/reports/preview` — free, rate-limited, returns ampel
- `POST /api/reports/create` — auth required, triggers background pipeline
- `POST /api/payments/checkout` — creates Stripe session
- `GET /api/reports/:id/pdf` — paid only

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

- `docs/CURSOR_BACKEND_PIPELINE.md` — DONE: mock→real pipeline migration
- `docs/CURSOR_EGMS_DATA_ANALYSIS.md` — DONE: data density confirmed (79 pts/500m urban)
- `docs/EGMS_DATA_REPORT.md` — DONE: full analysis results
- `docs/CURSOR_UX_SECURITY_AUDIT.md` — **CURRENT TASK**: security + UX fixes (prioritized list with file paths + line numbers)
