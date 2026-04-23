#!/usr/bin/env bash
# Diagnose whether the admin API is protected by ADMIN_TOKEN.
# Run directly on the server (URL-free for iOS Termius paste):
#     bash /opt/bodenbericht/scripts/check-admin-auth.sh
#
# Prints three sections:
#   1. which .env files exist
#   2. whether ADMIN_TOKEN is set and what its length is (never prints the value)
#   3. whether the admin API responds with 401 (good) or 200 (UNAUTHENTICATED - fix now)

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== .env files ==="
for f in "$REPO_ROOT/.env" "$REPO_ROOT/backend/.env"; do
  if [[ -f "$f" ]]; then
    printf "  exists  %s  (%d bytes)\n" "$f" "$(wc -c <"$f")"
  else
    printf "  missing %s\n" "$f"
  fi
done

echo
echo "=== ADMIN_TOKEN set? ==="
found=0
for f in "$REPO_ROOT/.env" "$REPO_ROOT/backend/.env"; do
  [[ -f "$f" ]] || continue
  line=$(grep -E '^ADMIN_TOKEN=' "$f" 2>/dev/null | head -1 || true)
  if [[ -n "$line" ]]; then
    value="${line#ADMIN_TOKEN=}"
    # Strip surrounding quotes if any
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"
    printf "  %s -> set, length %d chars\n" "$f" "${#value}"
    found=1
  else
    printf "  %s -> ADMIN_TOKEN not present\n" "$f"
  fi
done
[[ $found -eq 0 ]] && echo "  !! ADMIN_TOKEN is not defined in any .env file"

echo
echo "=== Admin API reachable, is it protected? ==="
# Test against the backend container on its published port; no Host header needed.
code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 4 \
  "http""://""127.0.0.1"":8000""/api""/_admin""/stats" || echo "ERR")
case "$code" in
  401) echo "  $code  OK - auth is enforced, token is required" ;;
  200) echo "  $code  !! OPEN - admin endpoints are publicly reachable, rotate ADMIN_TOKEN now" ;;
  000|ERR) echo "  $code  could not reach backend on 127.0.0.1:8000 - check 'docker compose ps'" ;;
  *)   echo "  $code  unexpected - investigate" ;;
esac

echo
echo "=== Done ==="
