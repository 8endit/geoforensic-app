#!/usr/bin/env bash
# Fetch the two Pexels photos into this directory. Run from anywhere:
#   bash /opt/bodenbericht/landing/images/photos/download.sh
#
# Pexels-Lizenz: free fuer kommerzielle Nutzung, keine Attributions-Pflicht
# (https://www.pexels.com/license/). Wir laden statt CDN-Hotlink lokal um
# DSGVO-clean zu bleiben (kein Third-Party-Image-Load beim Site-Visit).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

HOST="images.pexels.com"
SCHEME="https"

fetch() {
  local target="$1" id="$2"
  local url="${SCHEME}://${HOST}/photos/${id}/pexels-photo-${id}.jpeg?auto=compress&cs=tinysrgb&w=1920"
  echo "==> ${target} (Pexels ID ${id})"
  curl -sL -o "$target" "$url"
}

fetch hero-german-town.jpg 3489009
fetch waitlist-aerial-sunset.jpg 1637080

echo
echo "Done. Files in $HERE:"
ls -lh "$HERE"/*.jpg
