#!/usr/bin/env bash
# v4: gezielte Verifikation der HWRMRL-Services mit Timeout pro Call.
#
# v3 hatte 76 Services ohne Timeout durchgehen wollen → hing 30+ min.
# Service-Naming-Konvention HWRMRL_DE_{S|L}{L|M|H} steht für:
#   S = Hochwassergefahrenkarte (HWGK) — was wir wollen, zeigt Überflutung
#   L = Hochwasserrisikokarte (HWRK) — Schaden, Bevölkerung etc
#   L|M|H = Low/Medium/High probability = häufig / HQ100 / extrem
#
# Wir wollen die drei HWGK-Layer:
#   HWRMRL_DE_SL → HQ häufig
#   HWRMRL_DE_SM → HQ100
#   HWRMRL_DE_SH → HQ extrem

set -uo pipefail

BASE='https://geoportal.bafg.de'
UA='Mozilla/5.0'
TMP_DIR='/tmp/bfg-discovery'
mkdir -p "$TMP_DIR"

probe() {
  local svc="$1"
  local label="$2"
  local url="${BASE}/arcgis1/services/${svc}/MapServer/WMSServer?service=WMS&request=GetCapabilities"
  local out="${TMP_DIR}/wms_$(echo "$svc" | tr '/' '_').xml"
  local status size
  status=$(curl -sA "$UA" -m 8 -o "$out" -w '%{http_code}' "$url" 2>/dev/null) || status=000
  size=$(wc -c < "$out" 2>/dev/null || echo 0)
  printf "  %-30s  %-25s  HTTP %3s  %7d B" "$svc" "$label" "$status" "$size"
  if [ "$status" = "200" ] && [ "$size" -gt 2000 ] && grep -q '<Name>' "$out" 2>/dev/null; then
    echo "  ✓"
    grep -oE '<Name>[^<]+</Name>' "$out" | sed 's|<Name>||;s|</Name>||;s/^/      /'
    echo
    return 0
  else
    echo
    return 1
  fi
}

echo "=== HWRMRL-Services (Hochwasser-Gefahrenkarten DE) ==="
echo

probe "HWRMRL/HWRMRL_DE_SL" "HWGK haeufig (HQ häufig)"
probe "HWRMRL/HWRMRL_DE_SM" "HWGK mittel (HQ100)"
probe "HWRMRL/HWRMRL_DE_SH" "HWGK hoch (HQ extrem)"

echo
echo "=== Risikokarten (Fallback, falls HWGK keine Layer hat) ==="
echo

probe "HWRMRL/HWRMRL_DE_LL" "HWRK niedrig"
probe "HWRMRL/HWRMRL_DE_LM" "HWRK mittel"
probe "HWRMRL/HWRMRL_DE_LH" "HWRK hoch"

echo
echo "Fertig. Jeder grüne Haken oben ist ein gültiger WMS-Endpunkt."
echo "Schick den kompletten Output an Claude — daraus baue ich die"
echo "richtigen Env-Var-Werte für backend/.env."
