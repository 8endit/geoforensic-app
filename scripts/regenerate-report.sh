#!/usr/bin/env bash
# Regenerate the teaser PDF for an existing lead (for admin inspection).
#
# Runs backend/scripts/regenerate_report.py inside the backend container,
# then copies the resulting PDF(s) from /tmp/regenerated-reports/ in the
# container to ./regenerated-reports/ on the host.
#
# Usage (on the server):
#     bash /opt/bodenbericht/scripts/regenerate-report.sh <email>
#
# Example:
#     bash scripts/regenerate-report.sh stefan-8.9@gmx.de
#
# IMPORTANT — the PDF shown is the report as it would look TODAY with the
# current code and current backing data. It is NOT a historical replay of
# what was actually emailed to the recipient on the lead's created_at date.
# Section "Timeline context" below lists the backend commits that touched
# the report pipeline since the lead was created, so the reader can gauge
# how much has moved in the meantime.

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

EMAIL="${1:-}"
if [[ -z "$EMAIL" ]]; then
  echo "Usage: bash scripts/regenerate-report.sh <email>"
  echo "Example: bash scripts/regenerate-report.sh stefan-8.9@gmx.de"
  exit 2
fi

OUT_HOST_DIR="$REPO_ROOT/regenerated-reports"
mkdir -p "$OUT_HOST_DIR"

echo "=== Regenerating report(s) for $EMAIL ==="
echo
docker compose exec -T backend python -m backend.scripts.regenerate_report "$EMAIL"
RC=$?

echo "=== Copying PDFs from container to host ==="
# Make sure the directory inside the container exists and list what we got
container_id=$(docker compose ps -q backend)
if [[ -z "$container_id" ]]; then
  echo "  backend container not running, aborting"
  exit 3
fi

files_in_container=$(docker exec "$container_id" sh -c 'ls -1 /tmp/regenerated-reports/*.pdf 2>/dev/null' || true)
if [[ -z "$files_in_container" ]]; then
  echo "  no PDFs produced (no matching leads, or pipeline failed for all leads)"
else
  while IFS= read -r path_in_container; do
    name=$(basename "$path_in_container")
    docker cp "$container_id:$path_in_container" "$OUT_HOST_DIR/$name" >/dev/null
    printf "  %s  (%s bytes)\n" \
      "$OUT_HOST_DIR/$name" \
      "$(stat -c%s "$OUT_HOST_DIR/$name" 2>/dev/null || wc -c <"$OUT_HOST_DIR/$name")"
  done <<< "$files_in_container"
fi

echo
echo "=== Timeline context ==="
# Show commits to report-relevant files, plus a summary of how many happened
# after the oldest lead-related file timestamp we just wrote.
echo "  last 8 backend commits touching report pipeline:"
git log --oneline -8 -- \
  backend/app/html_report.py \
  backend/app/routers/leads.py \
  backend/app/soil_data.py \
  backend/app/email_service.py \
  backend/app/config.py \
  | sed 's/^/    /'

echo
echo "=== Done ==="
echo "PDFs are in:  $OUT_HOST_DIR/"
echo "Inspect with: docker compose cp / scp / or just open them in a PDF viewer."

exit $RC
