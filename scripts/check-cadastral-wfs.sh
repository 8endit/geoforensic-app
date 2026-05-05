#!/usr/bin/env bash
# Verify each Phase-1 INSPIRE Cadastral Parcels WFS endpoint by
# fetching its GetCapabilities document. Operator runs this on the
# VPS BEFORE rolling out app/cadastral.py changes — service URLs
# change occasionally after agency reorganisation.
#
# Aufruf:  bash scripts/check-cadastral-wfs.sh
# Output:  pro BL HTTP-Status + Antwort-Größe + erkannte WFS-Version

set -uo pipefail

UA="Bodenbericht/1.0 (kontakt@geoforensic.de)"

declare -A ENDPOINTS=(
  [NW]="https://www.wfs.nrw.de/geobasis/wfs_nw_inspire-flurstuecke_alkis"
  [BE]="https://gdi.berlin.de/services/wfs/alkis_flurstuecke"
  [HH]="https://geodienste.hamburg.de/HH_WFS_INSPIRE_Cadastral_Parcels"
  [SN]="https://geodienste.sachsen.de/wfs_geosn_alkis-cadastralparcels/guest"
  [TH]="https://www.geoproxy.geoportal-th.de/geoproxy/services/INSPIRE_CP"
  [BB]="https://inspire.brandenburg.de/services/cp_alkis_wfs"
  [MV]="https://www.geodaten-mv.de/dienste/inspire_cp_download_wfs"
  [SH]="https://service.gdi-sh.de/SH_INSPIRE_CP/wfs"
  [RP]="https://geo5.service24.rlp.de/wfs/inspire_lika"
  [SL]="https://geoportal.saarland.de/wfs/cp/cp_alkis"
  [ST]="https://www.geodatenportal.sachsen-anhalt.de/wss/service/INSPIRE_LSA_CADASTRAL/guest"
  [HB]="https://geodienste.bremen.de/wfs_inspire_cp"
)

printf "%-4s %-7s %-9s %s\n" "BL" "HTTP" "Bytes" "URL"
printf "%-4s %-7s %-9s %s\n" "----" "-------" "---------" "------------------------------------------------------"

for bl in "${!ENDPOINTS[@]}"; do
  url="${ENDPOINTS[$bl]}"
  full="${url}?service=WFS&request=GetCapabilities"
  resp=$(curl -sS -A "$UA" -m 10 -w "\n__HTTP__%{http_code}\n__SIZE__%{size_download}" "$full" 2>&1 || true)
  http=$(printf '%s\n' "$resp" | grep -oE '__HTTP__[0-9]+' | tr -d '__HTTP__')
  size=$(printf '%s\n' "$resp" | grep -oE '__SIZE__[0-9]+' | tr -d '__SIZE__')
  http=${http:-ERR}
  size=${size:-0}
  printf "%-4s %-7s %-9s %s\n" "$bl" "$http" "$size" "$url"
done

echo
echo "OK = HTTP 200 + > 1000 Bytes (GetCapabilities-XML üblicherweise 50-500 KB)"
echo "Bei HTTP != 200: URL hat sich geändert, in app/cadastral.py BUNDESLAND_ENDPOINTS aktualisieren"
