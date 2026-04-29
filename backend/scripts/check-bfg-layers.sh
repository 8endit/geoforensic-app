#!/usr/bin/env bash
# Verifiziert die echten BfG HWRM-WMS-Layer-Namen vom VPS aus.
#
# Erste Annahme aus DATA_SOURCES_VERIFIED.md (`/exts/InspireView/service`)
# liefert HTTP 500 "Extension not found". Stattdessen exploriert dieses
# Script den ArcGIS-REST-Service-Tree und probiert Standard-WMSServer-
# Endpunkte, bis wir ein gültiges WMS-Capabilities-XML finden.
#
# Nutzung: bash backend/scripts/check-bfg-layers.sh

set -uo pipefail

BASE='https://geoportal.bafg.de'
UA='Mozilla/5.0'
TMP_DIR='/tmp/bfg-discovery'
mkdir -p "$TMP_DIR"

fetch() {
  # fetch <url> <out> -> echo HTTP-Status
  local url="$1"
  local out="$2"
  curl -sA "$UA" -o "$out" -w '%{http_code}' "$url"
}

echo "=== Schritt 1 — Service-Verzeichnis (Root) ==="
ROOT_URL="${BASE}/arcgis1/rest/services?f=json"
status=$(fetch "$ROOT_URL" "${TMP_DIR}/root.json")
echo "HTTP $status, $(wc -c < "${TMP_DIR}/root.json") Bytes"
if [ "$status" = "200" ]; then
  echo "Folder + Services:"
  python3 -c "
import json, sys
try:
    d = json.load(open('${TMP_DIR}/root.json'))
    print('  Folders:', d.get('folders', []))
    print('  Services:')
    for s in d.get('services', []):
        print(f'    - {s.get(\"name\")} ({s.get(\"type\")})')
except Exception as e:
    print('  Parse error:', e)
" 2>/dev/null || cat "${TMP_DIR}/root.json" | head -20
fi
echo

echo "=== Schritt 2 — INSPIRE-Folder ==="
INSPIRE_URL="${BASE}/arcgis1/rest/services/INSPIRE?f=json"
status=$(fetch "$INSPIRE_URL" "${TMP_DIR}/inspire.json")
echo "HTTP $status, $(wc -c < "${TMP_DIR}/inspire.json") Bytes"
if [ "$status" = "200" ]; then
  python3 -c "
import json
try:
    d = json.load(open('${TMP_DIR}/inspire.json'))
    print('  Services im INSPIRE-Folder:')
    for s in d.get('services', []):
        print(f'    - {s.get(\"name\")} ({s.get(\"type\")})')
except Exception as e:
    print('  Parse error:', e)
" 2>/dev/null
fi
echo

echo "=== Schritt 3 — WMSServer-Endpunkte probieren ==="
# Mehrere Kandidaten-Pfade durchgehen; wer 200 + >2KB liefert, ist es.
CANDIDATES=(
  "${BASE}/arcgis1/services/INSPIRE/NZ/MapServer/WMSServer?service=WMS&request=GetCapabilities"
  "${BASE}/arcgis1/services/INSPIRE_NZ/MapServer/WMSServer?service=WMS&request=GetCapabilities"
  "${BASE}/arcgis1/services/HWRM/MapServer/WMSServer?service=WMS&request=GetCapabilities"
  "${BASE}/arcgis1/services/HWRM_AKTUELL/MapServer/WMSServer?service=WMS&request=GetCapabilities"
  "${BASE}/arcgis1/rest/services/INSPIRE/NZ/MapServer/WMSServer?service=WMS&request=GetCapabilities"
)

WINNING_URL=""
for url in "${CANDIDATES[@]}"; do
  out="${TMP_DIR}/cap-$(echo "$url" | md5sum | cut -d' ' -f1).xml"
  status=$(fetch "$url" "$out")
  size=$(wc -c < "$out")
  short=$(echo "$url" | sed "s|$BASE||")
  printf "  HTTP %s  %7d B  %s\n" "$status" "$size" "$short"
  if [ "$status" = "200" ] && [ "$size" -gt 2000 ]; then
    if grep -q '<Name>' "$out" 2>/dev/null; then
      WINNING_URL="$url"
      WINNING_OUT="$out"
    fi
  fi
done
echo

if [ -n "$WINNING_URL" ]; then
  echo "=== Schritt 4 — Layer-Namen aus dem funktionierenden Endpunkt ==="
  echo "Endpoint: $WINNING_URL"
  echo
  echo "Alle <Name>-Tags:"
  grep -oE '<Name>[^<]+</Name>' "$WINNING_OUT" \
    | sed 's|<Name>||;s|</Name>||' | nl
  echo
  echo "Hochwasser-relevante Namen (HQ / haeufig / extrem):"
  grep -oE '<Name>[^<]+</Name>' "$WINNING_OUT" \
    | sed 's|<Name>||;s|</Name>||' \
    | grep -iE 'hq|haeufig|haufig|extrem|hochwasser|flood' \
    || echo "  (keine direkten Treffer — schau die volle Liste oben an)"
else
  echo "=== Kein Standard-Endpunkt gefunden ==="
  echo
  echo "Mögliche Ursachen:"
  echo "  - Service-Name weicht von Annahmen ab → Schritt 1+2 prüfen"
  echo "  - Endpunkt blockt automatisierte Requests"
  echo "  - BfG hat die WMS-Bereitstellung umstrukturiert"
  echo
  echo "Nächster Schritt: Output von Schritt 1 + 2 an Claude, dann"
  echo "richten wir den Endpunkt manuell ein."
fi
