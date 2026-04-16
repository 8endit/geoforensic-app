#!/bin/bash
# Bodenbericht Server Setup - one-shot installation for Ubuntu 22.04+
# Run as root on a fresh Contabo/Hetzner VPS.
#
# Usage:
#   wget -qO- https://raw.githubusercontent.com/8endit/geoforensic-app/main/scripts/server-setup.sh | bash
# Or after cloning:
#   bash scripts/server-setup.sh

set -e

echo "=============================================="
echo "  Bodenbericht — Server Setup"
echo "=============================================="

# --- 1. System update ---
echo ""
echo "[1/7] System update..."
apt update -qq
apt upgrade -y -qq
apt install -y -qq docker.io docker-compose-plugin git ufw curl

systemctl enable docker
systemctl start docker

# --- 2. Firewall ---
echo ""
echo "[2/7] Firewall setup..."
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 8000/tcp  # Backend (temp, before nginx)
ufw --force enable

# --- 3. Clone repo ---
echo ""
echo "[3/7] Cloning repository..."
if [ ! -d "/opt/bodenbericht" ]; then
    git clone https://github.com/8endit/geoforensic-app.git /opt/bodenbericht
else
    cd /opt/bodenbericht && git pull
fi
cd /opt/bodenbericht

# --- 4. Generate secrets ---
echo ""
echo "[4/7] Generating secrets..."
if [ ! -f "backend/.env" ]; then
    ADMIN_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
    POSTGRES_PW=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")

    cat > backend/.env <<EOF
APP_NAME=bodenbericht-api
APP_VERSION=1.0.0
DEBUG=false

DATABASE_URL=postgresql+asyncpg://postgres:${POSTGRES_PW}@db:5432/geoforensic
POSTGRES_PASSWORD=${POSTGRES_PW}
SECRET_KEY=${SECRET_KEY}
ADMIN_TOKEN=${ADMIN_TOKEN}
ACCESS_TOKEN_EXPIRE_MINUTES=1440
JWT_ALGORITHM=HS256

# Stripe (leer lassen fuer Mock-Modus)
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_REPORT_PRICE_CENTS=4900

# SMTP - BITTE AUSFUELLEN (Brevo, Gmail, Resend, etc.)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=report@bodenbericht.de

# OAuth (spaeter)
GOOGLE_CLIENT_ID=
APPLE_CLIENT_ID=

# Paths
PUBLIC_BASE_URL=https://bodenbericht.de
RASTER_DIR=/opt/rasters
EOF

    # Root-level .env fuer docker-compose
    cat > .env <<EOF
POSTGRES_PASSWORD=${POSTGRES_PW}
RASTER_DIR=/opt/rasters
EOF

    echo ""
    echo "=============================================="
    echo "  WICHTIG: Speichere diese Zugangsdaten!"
    echo "=============================================="
    echo "  ADMIN_TOKEN:     ${ADMIN_TOKEN}"
    echo "  POSTGRES_PW:     ${POSTGRES_PW}"
    echo "  SECRET_KEY:      ${SECRET_KEY}"
    echo "=============================================="
    echo ""
fi

# --- 5. Rasters directory ---
echo ""
echo "[5/7] Raster directory..."
mkdir -p /opt/rasters

# --- 6. Start services ---
echo ""
echo "[6/7] Starting Docker services..."
docker compose up -d --build

sleep 5

# --- 7. Health check ---
echo ""
echo "[7/7] Health check..."
if curl -sf http://localhost:8000/api/health > /dev/null; then
    echo "  Backend: OK"
else
    echo "  Backend: FAILED - check 'docker compose logs backend'"
    exit 1
fi

echo ""
echo "=============================================="
echo "  Setup abgeschlossen!"
echo "=============================================="
echo ""
echo "Naechste Schritte:"
echo ""
echo "  1. SMTP konfigurieren:"
echo "     nano /opt/bodenbericht/backend/.env"
echo "     (SMTP_HOST, SMTP_USER, SMTP_PASSWORD eintragen)"
echo "     docker compose restart backend"
echo ""
echo "  2. Raster-Daten hochladen (vom lokalen Rechner):"
echo "     scp F:/jarvis-eye-data/geoforensic-rasters/* root@<IP>:/opt/rasters/"
echo ""
echo "  3. EGMS-Daten hochladen und importieren:"
echo "     scp -r F:/geoforensic-data/egms/NL root@<IP>:/opt/egms-nl"
echo "     docker exec -it bodenbericht-backend-1 python scripts/import_egms_parquet.py --country NL"
echo ""
echo "  4. Domain konfigurieren (DNS A-Record auf diese Server-IP)"
echo ""
echo "  5. SSL mit Certbot:"
echo "     apt install -y certbot"
echo "     certbot certonly --standalone -d bodenbericht.de"
echo ""
echo "Zugriffe:"
echo "  Landing:  http://\$(curl -s ifconfig.me):8000/"
echo "  Quiz:     http://\$(curl -s ifconfig.me):8000/landing/quiz.html"
echo "  Admin:    http://\$(curl -s ifconfig.me):8000/admin"
echo "  API:      http://\$(curl -s ifconfig.me):8000/api/health"
echo ""
echo "Admin-Token siehe oben — im Admin-Panel ins Feld oben rechts eingeben."
echo ""
