# Architektur — zwei getrennte Projekte

## Uebersicht

Das Produkt besteht aus **zwei separaten Deployments**, die ueber eine API verbunden sind:

```
┌─────────────────────────────┐       ┌────────────────────────────┐
│  Projekt 1: Bodenbericht    │       │  Projekt 2: Cozy-Frontend  │
│  (Pilot, aktuell live)      │       │  (Premium SaaS, spaeter)   │
├─────────────────────────────┤       ├────────────────────────────┤
│ Server: Hetzner CX22 (4EUR) │       │ Server: Vercel (gratis) +  │
│                             │       │         eigener API-Server │
│ Inhalt:                     │       │                            │
│ - Backend (FastAPI)         │       │ Inhalt:                    │
│ - PostGIS + EGMS-Daten      │ ────▶ │ - Next.js App              │
│ - SoilGrids Raster          │  API  │ - Modulare Reports         │
│ - Static Landing Pages      │       │ - Stripe Payments          │
│   /              (Hero)     │       │ - OAuth (Google/Apple)     │
│   /landing/quiz.html        │       │ - Dashboard                │
│   /admin (Dashboard)        │       │ - Premium Features         │
│                             │       │                            │
│ Domain: bodenbericht.de     │       │ Domain: geoforensic.de     │
└─────────────────────────────┘       └────────────────────────────┘
```

## Projekt 1: Bodenbericht (AKTIV)

**Repo:** `C:\dev\geoforensic-app\`  (GitHub: 8endit/geoforensic-app)

**Was drin ist:**
- `backend/` — FastAPI Backend + PostGIS + Report-Generierung
- `landing/` — Statische Landing Pages (Gregor's Design)
  - `index.html` — Marketing Page
  - `quiz.html` — Quiz-Funnel
  - `admin.html` — Admin Dashboard
- `docker-compose.yml` — DB + Backend
- `DEPLOYMENT.md` — Contabo/Hetzner Anleitung

**Zielgruppe:** B2C, Pilot, Lead-Magnet. Gratis Bodenbericht per Email.

**Status:** Ship-ready, wartet auf Server + SMTP.

## Projekt 2: Cozy-Frontend (SPAETER)

**Repo:** `C:\dev\cozy-frontend\cozy-frontend\`  (eigenes Repo, kein Git aktuell)

**Was drin ist:**
- Next.js 15 + React 19 App mit:
  - Landing (3D Hero mit R3F)
  - Adress-Autocomplete + Preview
  - Modulare Report-Auswahl (9 Module)
  - Auth (Email + Google + Apple OAuth)
  - Dashboard mit Reports, Rechnungen
  - Admin-Dashboard
  - Stripe Checkout
  - i18n (DE/EN/NL)
  - Legal-Seiten (Impressum, AGB, Datenschutz)

**Zielgruppe:** B2C + B2B, Premium SaaS, zahlende Kunden.

**Status:** Fertig gebaut, liegt rum. Kommt dran wenn Pilot erfolgreich ist.

## Saubere Trennung

### Das Backend (Projekt 1) kann BEIDE Frontends bedienen

Dieselbe API (`api.geoforensic.de`) bedient:
- **bodenbericht.de** (statische Landing + Quiz) → `POST /api/leads`
- **geoforensic.de** (cozy-frontend) → `POST /api/reports/create` + Auth + Stripe

Das heisst:
- Cozy-Backend-Code ist im Repo drin (`routers/auth.py`, `routers/payments.py`, `routers/reports.py`)
- Stoert den Pilot nicht (werden halt nicht aufgerufen)
- Ist da wenn cozy-frontend live geht

### Deployment-Strategie

**Phase 1 (jetzt):**
- Ein Hetzner-Server hostet alles
- Domain: `bodenbericht.de`
- Ein `docker-compose up -d` reicht

**Phase 2 (cozy-frontend Launch):**
- Zweites Deployment:
  - Vercel hostet cozy-frontend (gratis)
  - **Gleiches Backend** bedient beide Domains
  - `bodenbericht.de` → Hetzner (statische Landing)
  - `geoforensic.de` → Vercel → API-Calls zu Hetzner
- Alternative: Zweiter Hetzner-Server nur fuer geoforensic.de

**Phase 3 (Skalierung):**
- Backend-Server upgraden (CX32 oder CX42)
- Eventuell CDN (Cloudflare) davor
- DB-Replikation fuer Ausfallsicherheit

## Wann kommt Cozy?

**Triggers fuer Cozy-Launch:**
1. Pilot hat 100+ Leads und >5% Conversion-Rate
2. Ein zahlender Kunde waere bereit mehr als 49 EUR zu zahlen
3. B2B-Partner (Bank/Versicherung) will Dashboard-Zugang

**Bis dahin:** cozy-frontend einfach liegen lassen. Der Code verrottet nicht.
