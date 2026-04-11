# GeoForensic App

SaaS product: address-based ground motion risk reports for German properties.
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

## Current State (2026-04-11)

### Working
- Full auth flow (register, login, JWT, protected routes)
- Report CRUD (create, list, detail)
- Preview endpoint (free, rate-limited 10/hr)
- Stripe checkout flow (mock mode when no key)
- PDF/CSV download with auth token (fetch+blob)
- 3D particle hero with DOF
- Mobile-responsive header + menu

### NOT Working (Mock Data)
- `_mock_geocode()` — generates fake coords from SHA256, NOT real geocoding
- `_run_mock_report_pipeline()` — generates fake velocity, ampel, score from hash
- PDF endpoint returns plaintext pretending to be PDF
- Report data (geology, flood, slope) is all hardcoded
- No connection to real EGMS/InSAR data

### Next Steps
1. Replace `_mock_geocode` with Nominatim
2. Load EGMS data and query points within radius of address
3. Real analysis pipeline (velocity stats → ampel → geo_score)
4. Real PDF generation (reportlab/weasyprint) with map + charts
5. Promo code system + free tier (first 100 reports)
6. Deploy: Vercel (frontend) + Railway or Hetzner (backend + Postgres)

## Pricing

- **€199 per report** (`STRIPE_REPORT_PRICE_CENTS=19900`)
- Free preview (ampel + point count, no auth needed)
- Discussed but NOT implemented: first 100 free, promo codes, tiered pricing
- Competitors: UK BGS reports at £27-45, Germany has no equivalent service

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

## Related

- **geoforensic-karte**: Interactive map dashboard (separate repo, GitHub Pages)
  https://github.com/8endit/geoforensic-karte
- **EGMS**: EU InSAR data source — https://egms.land.copernicus.eu/
- **Data pipeline**: EGMS Ortho L3 → GeoTIFF → query by radius → report
