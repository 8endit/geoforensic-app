#!/usr/bin/env bash
# Smoke-Test: einen Vollbericht-Lead an die eigene E-Mail triggern.
#
# Nutzung auf dem VPS:
#     bash backend/scripts/smoke-vollbericht.sh
#
# Was passiert:
# 1. POST an /api/leads mit source="paid" → Vollbericht-Pfad
# 2. Adresse: Köln Hohenzollernring (Innenstadt, sollte NICHT in HQ-Zone)
# 3. E-Mail an benjaminweise41@gmail.com
# 4. Wartet 60 Sek, zeigt dann Backend-Logs für den Lead
#
# Erfolgsmarker:
# - Keine "BfG flood WMS HTTP 500"-Zeilen in den Logs
# - "Lead report sent" mit teaser=False
# - Mail kommt an mit Vollbericht (Bergbau / Hochwasser / KOSTRA-Sektionen
#   mit echten Daten statt "nicht erreichbar")
#
# Falls du eine zweite Test-Adresse willst (Hochwasser-Hotspot):
#     ADDRESS="Köln Rheinauhafen 1" bash backend/scripts/smoke-vollbericht.sh
# Diese Adresse liegt direkt am Rhein, sollte HQ-Zonen treffen.

set -euo pipefail

EMAIL="${EMAIL:-benjaminweise41@gmail.com}"
ADDRESS="${ADDRESS:-Köln Hohenzollernring 1}"
SOURCE="${SOURCE:-paid}"

echo "=== Test-Lead absetzen ==="
echo "  E-Mail:  $EMAIL"
echo "  Adresse: $ADDRESS"
echo "  Source:  $SOURCE  (→ Vollbericht-Pfad)"
echo

PAYLOAD=$(python3 -c "
import json
print(json.dumps({
    'email':   '$EMAIL',
    'address': '$ADDRESS',
    'source':  '$SOURCE',
}))
")

RESPONSE=$(docker compose exec -T backend curl -s -X POST \
  -H 'Content-Type: application/json' \
  -d "$PAYLOAD" \
  http://localhost:8000/api/leads)

echo "Response:"
echo "$RESPONSE"
echo

echo "=== Warte 60 Sekunden auf Background-Pipeline (Geocode + EGMS + WMS + PDF + Mail) ==="
for i in $(seq 60 -5 5); do
  printf "\r  noch %2d s..." "$i"
  sleep 5
done
printf "\r%-30s\n" "  fertig."
echo

echo "=== Backend-Logs (BfG, teaser-Flag, Lead-Status) ==="
docker compose logs --tail=80 backend 2>/dev/null | \
  grep -iE "BfG|flood|teaser=|Lead report|Static map|kostra|mining" | \
  tail -25

echo
echo "=== Letzter persistierter Report aus der DB ==="
docker compose exec -T db psql -U postgres geoforensic -c "
SELECT
  created_at,
  address_input,
  ampel,
  geo_score,
  (report_data->>'point_count')::int  AS pts,
  (report_data->>'is_teaser')::bool   AS is_teaser,
  report_data->'flood_bfg'            AS flood,
  report_data->'mining_nrw'           AS mining,
  report_data->'kostra'               AS kostra
FROM reports
WHERE address_input ILIKE '%${ADDRESS:0:5}%'
ORDER BY created_at DESC
LIMIT 1;
"
