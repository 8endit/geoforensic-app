#!/usr/bin/env bash
# Verifiziert die echten BfG HWRM-WMS-Layer-Namen vom VPS aus.
#
# v1: hartkodierter falscher Endpunkt (HTTP 500)
# v2: Discovery via INSPIRE/NZ (gefunden, aber nur generische
#     INSPIRE-NZ-Layer NZ.HazardArea / RiskZone / ObservedEvent —
#     keine HQ-pro-Szenario-Layer)
# v3: explore mehrere HWRM-relevante Folder die im Service-Tree
#     auftauchten (HWRMRL, flood3, nHWGK-HWRK), zeige pro Folder die
#     enthaltenen Services + WMS-Layer-Namen, damit wir die korrekte
#     Quelle für HQ_haeufig/HQ100/HQ_extrem identifizieren.

set -uo pipefail

BASE='https://geoportal.bafg.de'
UA='Mozilla/5.0'
TMP_DIR='/tmp/bfg-discovery'
mkdir -p "$TMP_DIR"

fetch() {
  local url="$1"; local out="$2"
  curl -sA "$UA" -o "$out" -w '%{http_code}' "$url"
}

list_services_in_folder() {
  local folder="$1"
  local url="${BASE}/arcgis1/rest/services/${folder}?f=json"
  local out="${TMP_DIR}/folder_${folder//\//_}.json"
  local status; status=$(fetch "$url" "$out")
  echo "  Folder: $folder  (HTTP $status, $(wc -c < "$out") B)"
  if [ "$status" = "200" ]; then
    python3 -c "
import json
try:
    d = json.load(open('$out'))
    for s in d.get('services', []):
        print(f'      - {s.get(\"name\")} ({s.get(\"type\")})')
    sub = d.get('folders', [])
    if sub:
        print(f'      (subfolders: {sub})')
except Exception as e:
    print(f'    parse error: {e}')
" 2>/dev/null
  fi
}

probe_wms() {
  # probe_wms <full-service-name e.g. "HWRMRL/Hochwassergefahr">
  local svc="$1"
  local url="${BASE}/arcgis1/services/${svc}/MapServer/WMSServer?service=WMS&request=GetCapabilities"
  local out="${TMP_DIR}/wms_$(echo "$svc" | tr '/' '_').xml"
  local status; status=$(fetch "$url" "$out")
  local size; size=$(wc -c < "$out")
  printf "    %s  HTTP %s  %7d B" "$svc" "$status" "$size"
  if [ "$status" = "200" ] && [ "$size" -gt 2000 ] && grep -q '<Name>' "$out" 2>/dev/null; then
    local layers; layers=$(grep -oE '<Name>[^<]+</Name>' "$out" | sed 's|<Name>||;s|</Name>||')
    local count; count=$(echo "$layers" | wc -l)
    echo "  ✓ ${count} Layer"
    echo "$layers" | sed 's/^/        /'
    echo
  else
    echo
  fi
}

echo "=== Schritt 1 — Folder mit HWRM-Bezug erkunden ==="
for folder in HWRMRL flood3 nHWGK-HWRK BFG; do
  list_services_in_folder "$folder"
done
echo

echo "=== Schritt 2 — WMS-Capabilities pro Service ziehen ==="
echo "(probiert für jeden gelisteten Service den /MapServer/WMSServer-Endpunkt)"
echo

# Service-Namen aus den JSON-Antworten extrahieren und je einen WMS-Probe-Call machen
SERVICES=$(python3 -c "
import json, glob, os
seen = set()
for path in glob.glob('${TMP_DIR}/folder_*.json'):
    try:
        d = json.load(open(path))
        for s in d.get('services', []):
            name = s.get('name')
            if name and s.get('type') == 'MapServer' and name not in seen:
                seen.add(name)
                print(name)
    except Exception:
        pass
" 2>/dev/null)

if [ -z "$SERVICES" ]; then
  echo "  Keine MapServer-Services gefunden in HWRMRL/flood3/nHWGK-HWRK/BFG."
  echo "  Wir bleiben bei INSPIRE/NZ — Code muss auf NZ.HazardArea umgestellt werden."
else
  while IFS= read -r svc; do
    [ -z "$svc" ] && continue
    probe_wms "$svc"
  done <<< "$SERVICES"
fi

echo
echo "=== Schritt 3 — INSPIRE/NZ Layer-Detail (Fallback) ==="
INSPIRE_URL="${BASE}/arcgis1/services/INSPIRE/NZ/MapServer/WMSServer?service=WMS&request=GetCapabilities"
fetch "$INSPIRE_URL" "${TMP_DIR}/inspire_nz.xml" > /dev/null
if [ -s "${TMP_DIR}/inspire_nz.xml" ] && grep -q '<Name>' "${TMP_DIR}/inspire_nz.xml" 2>/dev/null; then
  echo "  Layer in INSPIRE/NZ:"
  grep -oE '<Name>[^<]+</Name>' "${TMP_DIR}/inspire_nz.xml" | sed 's|<Name>||;s|</Name>||;s/^/    /'
fi
