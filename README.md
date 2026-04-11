# GeoForensic App

## Struktur

```
frontend/    <- Cozys Frontend (React/HTML/whatever)
backend/     <- API + Pipeline (FastAPI, wird von Claude Code geliefert)
docs/        <- API-Doku, Deployment Guide
```

## Fuer Cozy

Dein Frontend kommt in den `frontend/` Ordner. Push einfach alles rein.

Die API-Endpoints die dein Frontend ansprechen muss stehen in `docs/API.md`.

## Lokale Entwicklung

Backend laeuft auf `http://localhost:8000`
Frontend laeuft auf `http://localhost:5173` (oder was du nutzt)
