#!/bin/bash
# scripts/sync-launch-env.sh — pull the current launch-config keys into the
# live backend/.env on the VPS, then recreate the backend container so the
# new values take effect without a full image rebuild.
#
# What this script DOES:
#   - Backs up backend/.env to backend/.env.bak.<timestamp>.
#   - Idempotently upserts each launch-config key listed below in
#     `apply()`. If a key already has the desired value, it's a no-op.
#     If the key is missing, it's appended.
#   - Restarts only the backend container (db + redis stay up).
#   - Prints a verification line per touched key from the live container.
#
# What this script does NOT do:
#   - Touch any secret value (SMTP_USER, SMTP_PASSWORD, STRIPE_SECRET_KEY,
#     SECRET_KEY, ADMIN_TOKEN). Secrets stay where they are.
#   - Rebuild the backend image. If you need new app code, do
#     `git pull && docker compose build backend` first, then run this.
#
# Usage on the VPS:
#   cd /opt/bodenbericht
#   git pull
#   bash scripts/sync-launch-env.sh
#
# When new launch-config keys appear in main, extend the `apply` calls
# at the bottom and PR. The script is meant to drift in lockstep with
# what the operator actually wants live, not what backend/.env.example
# happens to default to (which is also dev defaults).

set -euo pipefail

ENV_FILE="backend/.env"
COMPOSE_SERVICE="backend"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE not found. Run this from /opt/bodenbericht (or the repo root)." >&2
  exit 1
fi

TS=$(date +%Y%m%d_%H%M%S)
BACKUP="$ENV_FILE.bak.$TS"
cp "$ENV_FILE" "$BACKUP"
echo "Backup written: $BACKUP"
echo ""

apply() {
  # Upsert KEY=VALUE in $ENV_FILE without touching anything else.
  # Reports current → new if changed, "already correct" if a no-op,
  # or "(appended)" if the key was missing.
  local key="$1" val="$2"
  if grep -qE "^${key}=" "$ENV_FILE"; then
    local cur
    cur=$(grep -E "^${key}=" "$ENV_FILE" | head -1 | cut -d= -f2-)
    if [ "$cur" = "$val" ]; then
      printf "  %-32s already correct\n" "$key"
    else
      # Use | as sed delimiter so values with / (URLs) don't break it.
      sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
      printf "  %-32s %s -> %s\n" "$key" "$cur" "$val"
    fi
  else
    echo "${key}=${val}" >> "$ENV_FILE"
    printf "  %-32s (appended) = %s\n" "$key" "$val"
  fi
}

echo "Applying launch-config to $ENV_FILE:"
apply "SMTP_FROM_EMAIL"            "bericht@bodenbericht.de"
apply "SMTP_FROM_NAME"             "Bodenbericht"
apply "STRIPE_REPORT_PRICE_CENTS"  "3900"
apply "STRIPE_CHECKOUT_SUCCESS_URL" "https://bodenbericht.de/danke?bericht=premium"
apply "STRIPE_CHECKOUT_CANCEL_URL"  "https://bodenbericht.de/?abbruch=1"
apply "PUBLIC_BASE_URL"            "https://bodenbericht.de"
# PROVENEXPERT_REVIEW_URL bleibt absichtlich draußen — Domenico setzt
# das händisch sobald das Profil existiert. Leerer Wert = mail-skip.

echo ""
echo "Recreating $COMPOSE_SERVICE container so new env values take effect..."
docker compose up -d --force-recreate "$COMPOSE_SERVICE"

echo ""
echo "Waiting 3 s for container to settle, then reading back live env:"
sleep 3
docker compose exec "$COMPOSE_SERVICE" env | \
  grep -E "^(SMTP_FROM_EMAIL|SMTP_FROM_NAME|STRIPE_REPORT_PRICE_CENTS|STRIPE_CHECKOUT_SUCCESS_URL|STRIPE_CHECKOUT_CANCEL_URL|PUBLIC_BASE_URL)=" | \
  sort

echo ""
echo "Done. Rollback if needed: cp $BACKUP $ENV_FILE && docker compose up -d --force-recreate $COMPOSE_SERVICE"
