# GeoForensic App — Backend + Frontend-Anbindung

## Context

Cozys Frontend (Next.js 15 / React 19) steht als Landing Page mit 3D-Hero und PropertyForm.
Das Backend-Verzeichnis ist leer. Die komplette API-Spec existiert in `docs/API.md`.
Ziel: FastAPI-Backend nach Spec bauen, Frontend vollständig anbinden (Auth, Reports, Preview, Payments).

---

## Phase 1: Backend (FastAPI + PostgreSQL)

### 1.1 Projekt-Struktur

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, CORS, router includes
│   ├── config.py             # Settings via pydantic-settings (.env)
│   ├── database.py           # SQLAlchemy async engine + session
│   ├── models.py             # ORM models: User, Report, Payment
│   ├── schemas.py            # Pydantic request/response schemas
│   ├── auth.py               # JWT creation/verification, password hashing
│   ├── dependencies.py       # get_current_user, get_db
│   └── routers/
│       ├── __init__.py
│       ├── auth.py           # POST /api/auth/register, /login, GET /me
│       ├── reports.py        # CRUD + preview + PDF/CSV download
│       ├── payments.py       # Stripe checkout + webhook
│       └── health.py         # GET /api/health
├── alembic/                  # DB migrations
├── alembic.ini
├── requirements.txt
├── Dockerfile
└── .env.example
```

### 1.2 Datenbank-Modelle

**User**: id (UUID), email (unique), password_hash, company_name?, gutachter_type?, created_at

**Report**: id (UUID), user_id (FK), address_input, latitude, longitude, radius_m, aktenzeichen?, status (processing/completed/failed), ampel (gruen/gelb/rot), geo_score, paid (bool), report_data (JSONB), pdf_path?, created_at

**Payment**: id (UUID), report_id (FK), stripe_session_id, status, amount, created_at

### 1.3 API-Endpoints (exakt nach docs/API.md)

| Endpoint | Auth | Beschreibung |
|----------|------|-------------|
| `POST /api/auth/register` | Nein | User anlegen, JWT zurück |
| `POST /api/auth/login` | Nein | Login, JWT zurück |
| `GET /api/auth/me` | JWT | User-Profil |
| `POST /api/reports/preview` | Nein | Kostenloser Schnell-Check (rate-limited 10/h pro IP) |
| `POST /api/reports/create` | JWT | Report erstellen → Status "processing" |
| `GET /api/reports` | JWT | Alle Reports des Users |
| `GET /api/reports/:id` | JWT | Einzel-Report mit Analyse-Daten |
| `GET /api/reports/:id/pdf` | JWT | PDF-Download (402 wenn !paid) |
| `GET /api/reports/:id/raw.csv` | JWT | CSV-Download (402 wenn !paid) |
| `POST /api/payments/checkout` | JWT | Stripe Checkout-Session erstellen |
| `POST /api/payments/webhook` | Nein | Stripe Webhook → paid=true |
| `GET /api/health` | Nein | Status-Check |

### 1.4 Kern-Dependencies

```
fastapi, uvicorn[standard]
sqlalchemy[asyncio], asyncpg, alembic
pydantic-settings
python-jose[cryptography]     # JWT
passlib[bcrypt]               # Password hashing
stripe                        # Payments
slowapi                       # Rate limiting für Preview
```

### 1.5 CORS

```python
origins = [
    "http://localhost:3000",      # Next.js dev
    "https://geoforensic.de",    # Production
]
```

### 1.6 Report-Pipeline (Stub)

Beim `POST /api/reports/create` wird ein Background-Task gestartet der:
1. Adresse geocodiert (Nominatim/OpenCage)
2. Punkte im Radius sammelt (Stub: Mock-Daten für MVP)
3. Ampel + GeoScore berechnet
4. Report-Status auf "completed" setzt

Für den MVP reicht ein **Stub mit realistischen Mock-Daten**. Die echte Pipeline (InSAR, Geologie-APIs) kommt später.

---

## Phase 2: Frontend-Anbindung

### 2.1 API-Service Layer

**Neue Datei**: `frontend/geoforensic_webcode/lib/api.ts`

```
- API_URL aus NEXT_PUBLIC_API_URL env var
- fetchApi() Wrapper: setzt Content-Type, Bearer Token aus localStorage, Error-Handling
- Funktionen: register(), login(), getMe(), createReport(), getReports(), getReport(), previewReport(), checkout()
```

### 2.2 Auth-State Management

**Neue Datei**: `frontend/geoforensic_webcode/lib/auth-context.tsx`

- React Context mit user, token, login(), logout(), register()
- Token in localStorage, User-State im Context
- Provider in layout.tsx wrappen

### 2.3 Environment

**Neue Datei**: `frontend/geoforensic_webcode/.env.local`
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2.4 Neue Seiten

| Route | Beschreibung |
|-------|-------------|
| `/login` | Login-Formular → POST /api/auth/login |
| `/register` | Registrierung → POST /api/auth/register |
| `/dashboard` | Liste aller Reports + "Neuer Report" Button |
| `/reports/[id]` | Report-Detail mit Ampel, Score, Karte, PDF-Download |

### 2.5 PropertyForm Umbau

`components/property-form.tsx` — aktuell nur `console.log`:

1. Adresse aus street + postalCity zusammenbauen
2. **Ohne Auth**: `POST /api/reports/preview` aufrufen → Ampel + point_count anzeigen
3. **Mit Auth**: Button "Vollständigen Report erstellen" → `POST /api/reports/create` → Redirect zu `/reports/[id]`
4. Loading-State + Error-Toast (sonner ist schon installiert)

### 2.6 Ergebnis-Komponente

**Neue Datei**: `components/preview-result.tsx`
- Ampel-Anzeige (grün/gelb/rot mit Farbe + Icon)
- Punkt-Anzahl + aufgelöste Adresse
- CTA: "Vollständigen Report kaufen" → Login/Register falls nicht eingeloggt

### 2.7 Report-Detail-Seite

- Ampel + GeoScore prominient
- Analyse-Daten aus report_data (Geologie, Flood, Slope)
- Wenn !paid → "Report kaufen" → Stripe Checkout
- Wenn paid → PDF- und CSV-Download Buttons

### 2.8 Header Update

`components/header.tsx`:
- "Sign In" Link → `/login` (statt `#sign-in`)
- Wenn eingeloggt: "Dashboard" Link + User-Avatar/Name

---

## Phase 3: Docker & Deployment

### 3.1 Docker Compose (Lokale Entwicklung)

```
docker-compose.yml
├── backend   (FastAPI, port 8000)
├── db        (PostgreSQL 16, port 5432)
└── frontend  (Next.js dev, port 3000)
```

### 3.2 Env Files

- `backend/.env.example` — SECRET_KEY, DATABASE_URL, STRIPE_KEY_SECRET, etc.
- `frontend/geoforensic_webcode/.env.example` — NEXT_PUBLIC_API_URL, NEXT_PUBLIC_STRIPE_KEY

---

## Reihenfolge der Umsetzung

1. **Backend Grundgerüst** — main.py, config, database, models, schemas
2. **Auth-Endpoints** — register, login, me + JWT
3. **Preview-Endpoint** — kostenloser Schnell-Check mit Mock-Daten
4. **Reports CRUD** — create, list, get + Background-Task Stub
5. **Payments** — Stripe Checkout + Webhook
6. **Frontend: API-Service + Auth-Context** — lib/api.ts, auth-context.tsx, .env.local
7. **Frontend: PropertyForm → Preview** — API-Call + Ergebnis-Anzeige
8. **Frontend: Auth-Seiten** — /login, /register
9. **Frontend: Dashboard + Report-Detail** — /dashboard, /reports/[id]
10. **Frontend: Header Update** — Auth-aware Navigation
11. **Docker Compose** — lokales Setup

## Verifikation

- Backend: `uvicorn app.main:app --reload` → Swagger unter /docs
- Frontend: `pnpm dev` → Form Submit → Preview-Ergebnis
- Auth-Flow: Register → Login → Dashboard → Report erstellen → Stripe (Testmodus) → PDF
- Health-Check: `GET /api/health` → `{ status: "ok" }`

## Kritische Dateien

**Bestehend (ändern):**
- `frontend/geoforensic_webcode/components/property-form.tsx` — API-Anbindung
- `frontend/geoforensic_webcode/components/header.tsx` — Auth-aware Nav
- `frontend/geoforensic_webcode/app/layout.tsx` — AuthProvider wrappen
- `frontend/geoforensic_webcode/app/page.tsx` — Preview-Result einbinden
- `frontend/geoforensic_webcode/next.config.ts` — API rewrites/proxy optional

**Neu (erstellen):**
- `backend/` — komplettes FastAPI-Projekt
- `frontend/geoforensic_webcode/lib/api.ts`
- `frontend/geoforensic_webcode/lib/auth-context.tsx`
- `frontend/geoforensic_webcode/app/login/page.tsx`
- `frontend/geoforensic_webcode/app/register/page.tsx`
- `frontend/geoforensic_webcode/app/dashboard/page.tsx`
- `frontend/geoforensic_webcode/app/reports/[id]/page.tsx`
- `frontend/geoforensic_webcode/components/preview-result.tsx`
- `docker-compose.yml`
