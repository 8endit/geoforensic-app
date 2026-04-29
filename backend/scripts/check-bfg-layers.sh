#!/usr/bin/env bash
# Verifiziert die echten BfG HWRM-WMS-Layer-Namen vom VPS aus.
#
# Hintergrund: backend/app/flood_data.py benutzt Default-Layer-Namen
# HQ_haeufig / HQ100 / HQ_extrem die Best-Guess aus Sekundärquellen sind.
# Die Cloud-Sandbox kommt nicht an den ArcGIS-Endpunkt ran (HTTP 403),
# vom VPS oder aus QGIS funktioniert er. Dieses Script zieht die
# Capabilities und extrahiert die echten <Name>-Strings.
#
# Nutzung: bash backend/scripts/check-bfg-layers.sh
#
# Falls die Default-Namen falsch sind, in /opt/bodenbericht/backend/.env
# entsprechend setzen:
#     BFG_FLOOD_LAYER_HAEUFIG=<echter Name>
#     BFG_FLOOD_LAYER_HQ100=<echter Name>
#     BFG_FLOOD_LAYER_EXTREM=<echter Name>
# Danach `docker compose restart backend`.

set -euo pipefail

URL='https://geoportal.bafg.de/arcgis1/rest/services/INSPIRE/NZ/MapServer/exts/InspireView/service'
CAP_PARAMS='?service=WMS&request=GetCapabilities&version=1.3.0'
OUT='/tmp/bfg-capabilities.xml'

echo "=== Schritt 1 — Capabilities ziehen ==="
http_status=$(curl -sA 'Mozilla/5.0' -o "$OUT" -w '%{http_code}' "${URL}${CAP_PARAMS}")
echo "HTTP $http_status, $(wc -c < "$OUT") Bytes nach $OUT"
echo

if [ "$http_status" != "200" ]; then
  echo "FEHLER: HTTP $http_status — Endpunkt antwortet nicht mit 200."
  echo "Erste 500 Zeichen der Antwort:"
  head -c 500 "$OUT"
  echo
  exit 1
fi

if [ "$(wc -c < "$OUT")" -lt 500 ]; then
  echo "FEHLER: Antwort zu kurz, vermutlich kein gültiges Capabilities-XML."
  echo "Inhalt:"
  cat "$OUT"
  exit 1
fi

echo "=== Schritt 2 — Layer-Namen extrahieren ==="
echo "Alle <Name>-Tags im Capabilities-XML:"
echo
grep -oE '<Name>[^<]+</Name>' "$OUT" | sed 's|<Name>||;s|</Name>||' | nl
echo

echo "=== Schritt 3 — Defaults gegen gefundene Namen abgleichen ==="
for default_name in HQ_haeufig HQ100 HQ_extrem; do
  if grep -qE "<Name>${default_name}</Name>" "$OUT"; then
    echo "  $default_name             vorhanden im XML"
  else
    echo "  $default_name             NICHT gefunden — vermutlich falsch"
  fi
done
echo

echo "=== Schritt 4 — Hochwasser-relevante Namen heuristisch suchen ==="
echo "Layer-Namen die 'HQ' oder 'haeufig' oder 'extrem' enthalten:"
grep -oE '<Name>[^<]+</Name>' "$OUT" \
  | sed 's|<Name>||;s|</Name>||' \
  | grep -iE 'hq|haeufig|haufig|extrem|hochwasser|flood' \
  || echo "  (keine Treffer — Layer-Namen sind komplett anders)"
