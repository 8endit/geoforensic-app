# Deployment Guide — Bodenbericht

## Voraussetzungen

- Server: Contabo VPS (6 EUR/Mo) oder Hetzner CX22 (4 EUR/Mo)
- OS: Ubuntu 22.04+
- Docker + Docker Compose
- Domain: bodenbericht.de (oder geoforensic.de)

## 1. Server einrichten

```bash
ssh root@<server-ip>
apt update && apt upgrade -y
apt install -y docker.io docker-compose-plugin git
systemctl enable docker
```

## 2. Repository klonen

```bash
cd /opt
git clone https://github.com/8endit/geoforensic-app.git
cd geoforensic-app
```

## 3. Daten hochladen

Folgende Dateien von lokal auf den Server kopieren:

```bash
# Vom lokalen Rechner:
scp -r F:/jarvis-eye-data/geoforensic-rasters/ root@<server-ip>:/opt/rasters/
scp -r F:/geoforensic-data/egms/NL/ root@<server-ip>:/opt/egms-nl/
```

Enthaltene Dateien:
- `soilgrids_*_nlde.tif` (6 Raster, ~64 MB) — pH, SOC, Textur, Dichte
- `lucas_soil_de.csv` (272 KB) — Schwermetalle + Naehrstoffe
- `lucas_pesticides_nuts2.xlsx` (~200 KB) — 118 Substanzen auf NUTS2-Ebene.
  Erwartetes Format: erste Spalte `NUTS2` (DE-Codes wie `DE11`, `DE21`…),
  weitere Spalten numerisch je Substanz. Backend logged beim Startup:
  `PesticideLookup: N NUTS2 regions, M substances from …`. Abweichende
  Header-Namen werden erkannt (`NUTS_ID`, `nuts_id`, `region`), Feature
  deaktiviert sich still wenn Datei fehlt oder Struktur nicht passt.
- EGMS NL Parquets (1.2 GB) — Bodenbewegungsdaten

## 4. Environment konfigurieren

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Ausfuellen:
```env
SECRET_KEY=<zufaelliger-langer-string>
POSTGRES_PASSWORD=<sicheres-passwort>

# SMTP (Gmail mit App-Passwort oder Transactional Service)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=report@bodenbericht.de
SMTP_PASSWORD=<app-passwort>
SMTP_FROM_EMAIL=report@bodenbericht.de

# Raster-Daten Pfad auf dem Server
RASTER_DIR=/opt/rasters

PUBLIC_BASE_URL=https://bodenbericht.de
```

## 5. Docker starten

```bash
# .env fuer docker-compose
echo "RASTER_DIR=/opt/rasters" > .env
echo "POSTGRES_PASSWORD=<sicheres-passwort>" >> .env

docker compose up -d
```

## 6. EGMS-Daten importieren

```bash
# In den Container oder lokal mit Python:
docker exec -it geoforensic-app-backend-1 \
  python scripts/import_egms_parquet.py --country NL

# Oder lokal:
DATABASE_URL="postgresql://postgres:<pw>@<server-ip>:5432/geoforensic" \
  python backend/scripts/import_egms_parquet.py --country NL
```

Verifizieren:
```bash
docker exec geoforensic-app-db-1 \
  psql -U postgres -d geoforensic -c "SELECT COUNT(*) FROM egms_points;"
# Erwartung: 3,254,620
```

## 7. SSL mit Certbot

```bash
apt install -y certbot
certbot certonly --standalone -d bodenbericht.de
```

Nginx als Reverse Proxy (optional):
```bash
apt install -y nginx
```

## 8. Testen

```bash
# Health Check
curl https://bodenbericht.de/api/health

# Landing Page
curl -s -o /dev/null -w "%{http_code}" https://bodenbericht.de/

# Lead Submit (sendet Email wenn SMTP konfiguriert)
curl -X POST https://bodenbericht.de/api/leads \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.de","address":"Marienplatz 1, Muenchen","source":"test"}'
```

## Was spaeter heruntergeladen werden kann

| Daten | Wann | Wie |
|-------|------|-----|
| EGMS DE | Wenn DE-Markt startet | Copernicus EGMS Portal → Parquet → import_egms_parquet.py |
| LUCAS Pestizide NL-Punkte | Wenn ESDAC genehmigt | Excel in Raster-Dir kopieren |
| SoilGrids Updates | Bei neuen Releases (~selten) | WCS Download, _nlde.tif ersetzen |
| CORINE Update | Alle 6 Jahre | Copernicus Land → GeoTIFF |

## Checkliste vor Go-Live

- [ ] `backend/.env` mit echten Credentials
- [ ] EGMS-Daten importiert (3.25M+ Punkte)
- [ ] SoilGrids Raster gemountet
- [ ] SMTP funktioniert (Test-Email senden)
- [ ] SSL-Zertifikat aktiv
- [ ] Landing Page erreichbar
- [ ] Quiz-Submit liefert PDF per Email
- [ ] Gregor: Landing Page Claims geprueft
- [ ] DNS A-Record auf Server-IP
