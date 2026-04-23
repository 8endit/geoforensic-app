#!/usr/bin/env bash
# Delete test/developer leads from the leads table.
#
# Runs dry-run by default (SELECT only, nothing deleted). Pass --confirm to
# actually delete. The list of test emails is hardcoded below — edit to taste
# before running.
#
# Usage (on the server):
#     bash /opt/bodenbericht/scripts/delete-test-leads.sh           # preview
#     bash /opt/bodenbericht/scripts/delete-test-leads.sh --confirm # delete

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

EMAILS_TO_DELETE=(
  "benjaminweise41@gmail.com"
  "weise.benjamin@gmx.de"
)

MODE="${1:-}"

# Build 'email1','email2',... for the IN clause
EMAIL_SQL=$(printf "'%s'," "${EMAILS_TO_DELETE[@]}")
EMAIL_SQL="${EMAIL_SQL%,}"

echo "=== Leads currently in DB matching those emails ==="
docker compose exec -T db psql -U postgres -d geoforensic -c "
  SELECT
    created_at::timestamp(0) AS created_at,
    email,
    source,
    COALESCE(quiz_answers->>'address', '-') AS address
  FROM leads
  WHERE email IN ($EMAIL_SQL)
  ORDER BY created_at DESC;
"

if [[ "$MODE" == "--confirm" ]]; then
  echo
  echo "=== Deleting now... ==="
  docker compose exec -T db psql -U postgres -d geoforensic -c "
    DELETE FROM leads
    WHERE email IN ($EMAIL_SQL)
    RETURNING email, source, created_at::timestamp(0);
  "
  echo
  echo "Done. Refresh the admin dashboard to verify the rows are gone."
else
  echo
  echo "Dry-run only. To actually delete, re-run with:"
  echo "    bash scripts/delete-test-leads.sh --confirm"
fi
