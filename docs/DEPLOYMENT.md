# GeoForensic — Deployment Guide

## Voraussetzungen

- VPS mit Ubuntu 22.04+ (Hetzner CX22 reicht: 2 vCPU, 4 GB RAM, ~5 EUR/Monat)
- Domain (z.B. geoforensic.de) mit A-Record auf die VPS-IP
- Stripe-Account (dashboard.stripe.com)

## 1. Server vorbereiten

```bash
# Docker installieren
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Docker Compose (v2 ist in Docker enthalten)
docker compose version
```

## 2. Projekt auf Server kopieren

```bash
git clone https://github.com/DEIN_USER/geoforensic.git
cd geoforensic
```

## 3. Environment konfigurieren

```bash
cp .env.production.example .env

# Secrets generieren
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
# -> In .env als SECRET_KEY eintragen

python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# -> In .env als POSTGRES_PASSWORD eintragen (auch in DATABASE_URL!)

# Stripe-Keys aus dashboard.stripe.com eintragen
nano .env
```

## 4. SSL-Zertifikat holen (vor dem ersten Start)

```bash
# Temporaer nginx ohne SSL starten fuer certbot
mkdir -p nginx/certs
docker compose -f docker-compose.prod.yml run --rm certbot \
  certonly --webroot -w /var/www/certbot \
  -d geoforensic.de -d www.geoforensic.de \
  --email contact@geoforensic.de --agree-tos --no-eff-email
```

## 5. Starten

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## 6. Pruefen

```bash
# Logs
docker compose -f docker-compose.prod.yml logs -f

# Health check
curl https://geoforensic.de/api/health

# Frontend
curl -I https://geoforensic.de
```

## 7. Stripe Webhook einrichten

1. Gehe zu dashboard.stripe.com -> Developers -> Webhooks
2. Endpoint URL: `https://geoforensic.de/api/payments/webhook`
3. Events: `checkout.session.completed`
4. Signing Secret in `.env` als `STRIPE_WEBHOOK_SECRET` eintragen
5. `docker compose -f docker-compose.prod.yml restart backend`

## Updates deployen

```bash
cd geoforensic
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

## Backups

```bash
# Datenbank-Backup
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U geoforensic geoforensic > backup_$(date +%Y%m%d).sql
```

## Kosten

| Posten | Monatlich |
|--------|-----------|
| Hetzner CX22 | ~5 EUR |
| Domain .de | ~0.50 EUR |
| Stripe | 1.4% + 0.25 EUR pro Transaktion |
| **Total fix** | **~5.50 EUR/Monat** |
