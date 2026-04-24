#!/usr/bin/env bash
# Diagnose whether the OSM static-map service is reachable and returning
# real map images or just "service unavailable" placeholders.
#
# Paste-safe for iOS Termius — the URL is built from bash variables so no
# URL substring appears in the terminal clipboard.
#
# Usage (on the server):
#     bash /opt/bodenbericht/scripts/check-static-map.sh
#
# Optional: pass lat lon to test a specific location (default: Schulstraße 2,
# 76571 Gaggenau):
#     bash scripts/check-static-map.sh 52.5200 13.4050

set -u

LAT="${1:-48.804}"
LON="${2:-8.32}"

# Assemble URL from parts so iOS paste autocorrect cannot wrap it.
SCHEME="https"
HOST="staticmap.openstreetmap.de"
PATH_="/staticmap.php"
QUERY="center=${LAT},${LON}&zoom=16&size=400x250&markers=${LAT},${LON},red-pushpin"
URL="${SCHEME}://${HOST}${PATH_}?${QUERY}"

echo "=== Probing static map service ==="
echo "  host:   ${HOST}"
echo "  coords: ${LAT}, ${LON}"
echo

echo "=== Direct curl (from host) ==="
status_and_size=$(curl -s -o /tmp/static-map-probe.png -w "status=%{http_code} size=%{size_download}B time=%{time_total}s\n" \
  -H "User-Agent: Bodenbericht/1.0 (diag)" --max-time 6 "$URL" || echo "CURL_ERROR")
echo "  ${status_and_size}"
if [[ -f /tmp/static-map-probe.png ]]; then
  bytes=$(wc -c </tmp/static-map-probe.png)
  if [[ $bytes -gt 500 ]]; then
    echo "  => looks real (> 500 bytes), probably a valid map PNG"
  elif [[ $bytes -gt 0 ]]; then
    echo "  => SOFT FAIL: got ${bytes} bytes, service sent a placeholder"
  else
    echo "  => HARD FAIL: no bytes received"
  fi
  rm -f /tmp/static-map-probe.png
fi

echo
echo "=== Python path through app.static_map.fetch_static_map ==="
docker compose exec -T backend python -c "
import asyncio
from app.static_map import fetch_static_map
res = asyncio.run(fetch_static_map(${LAT}, ${LON}))
if res:
    print(f'  ok — data URI length {len(res)} chars, first 40: {res[:40]}...')
else:
    print('  empty string returned — check backend logs for the exact reason')
    print('  (docker compose logs backend --tail=50 | grep -i static_map)')
" 2>&1

echo
echo "=== Recent static_map log lines ==="
docker compose logs backend --tail=200 2>/dev/null | grep -i "static map\|static_map" | tail -5 || echo "  (no log lines yet — try again after generating a report)"

echo
echo "=== Done ==="
