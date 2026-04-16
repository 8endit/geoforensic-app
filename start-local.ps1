# Start GeoForensic Backend lokal (ohne Docker fuer Backend)
# Voraussetzung: PostGIS laeuft in Docker (docker compose up -d db)

Write-Host "=== Starting GeoForensic Backend (local) ===" -ForegroundColor Green

# 1. Starte nur PostGIS in Docker (falls nicht laeuft)
Write-Host "Starting PostGIS..." -ForegroundColor Yellow
docker compose up -d db 2>$null

# 2. Warte bis DB ready
Start-Sleep -Seconds 3

# 3. Starte Backend direkt mit Python
Write-Host "Starting Backend on http://localhost:8000 ..." -ForegroundColor Yellow
Set-Location backend
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/geoforensic"
$env:RASTER_DIR = "F:/jarvis-eye-data/geoforensic-rasters"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
