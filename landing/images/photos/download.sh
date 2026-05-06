#!/usr/bin/env bash
# Fetch all Pexels photos used as hero backgrounds into this directory.
# Run from anywhere:
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
  local url="${SCHEME}://${HOST}/photos/${id}/pexels-photo-${id}.jpeg?auto=compress&cs=tinysrgb&w=2560"
  echo "==> ${target} (Pexels ID ${id})"
  curl -sL -o "$target" "$url"
}

# Bestand seit 2026-04 (Hauptseite-Hero + Premium-Section-Hero)
fetch hero-german-town.jpg        3489009
fetch waitlist-aerial-sunset.jpg  1637080

# Erweitert 2026-05-06 — 10 Pexels-Photos fuer die ~17 Pages mit
# vorherigem `hero-gradient`-Grid-Pattern. Themen-Mapping siehe
# `<style>`-Bloecke pro Page (`.hero-photo { background-image: ... }`).
fetch hero-setzungsriss.jpg          10587372  # Riss in Wand + Stufen
fetch hero-haende-erde.jpg           27176773  # Haende in Erde mit Pflanzen
fetch hero-hochbeete-aufsicht.jpg    27033658  # Hochbeete von oben
fetch hero-garten-hochbeete.jpg       9685943  # Hochbeete in gepflegtem Garten
fetch hero-satellit-winter.jpg          23781  # Sentinel-Look ueber Winter-Erde
fetch hero-feldweg-acker.jpg         32544961  # DE-Feldweg + Funkmast
fetch hero-reihenhaus-de.jpg         34438667  # DE-Reihenhaeuser ueber Bruecke
fetch hero-rotes-gartenhaus.jpg      32432597  # Rotes Schwedenhaus im Garten
fetch hero-maehdrescher.jpg          17450309  # Maehdrescher im Weizenfeld
fetch hero-satellit-erde.jpg         30596893  # Satellit-Render ueber Erde

echo
echo "Done. Files in $HERE:"
ls -lh "$HERE"/*.jpg
