#!/usr/bin/env bash
# Fetch the two Pexels photos into this directory. Run from anywhere:
#   bash /opt/bodenbericht/landing/images/photos/download.sh
# Exists because iOS Termius auto-wraps pasted URLs with <> which kills wget.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

HOST="images.pexels.com"
SCHEME="https"

fetch() {
  local target="$1" id="$2"
  local url="${SCHEME}://${HOST}/photos/${id}/pexels-photo-${id}.jpeg?auto=compress&cs=tinysrgb&w=1920"
  echo "==> ${target} (Pexels ID ${id})"
  wget --quiet --show-progress -O "$target" "$url"
}

fetch hero-german-town.jpg 3489009
fetch waitlist-aerial-sunset.jpg 1637080

echo
echo "Done. Files in $HERE:"
ls -lh "$HERE"/*.jpg
