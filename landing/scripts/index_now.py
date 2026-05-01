#!/usr/bin/env python3
"""IndexNow-Push für bodenbericht.de.

Pingt Bing/Yandex (und damit Copilot/ChatGPT-Web, die über die gleichen
Indizes laufen) nach jedem Deploy. Beschleunigt KI-Indexierung um Tage
gegenüber dem klassischen Sitemap-Crawl-Zyklus.

API: https://www.indexnow.org/documentation
- Key-File MUSS unter https://bodenbericht.de/<KEY>.txt erreichbar sein
  und exakt den Key als Inhalt enthalten (siehe landing/<KEY>.txt).
- Wird der Key im Webroot nicht gefunden, lehnt IndexNow den Ping ab.

Usage:
    python landing/scripts/index_now.py            # alle URLs aus sitemap.xml
    python landing/scripts/index_now.py /pilot     # einzelne URL
    python landing/scripts/index_now.py --dry-run  # nur loggen, nicht senden

Exit-Code 0 auch bei IndexNow-200/202; alles >=400 wird geloggt aber
führt nicht zum Deploy-Abbruch (IndexNow ist best-effort).
"""

from __future__ import annotations

import argparse
import logging
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import HTTPError, URLError

INDEXNOW_KEY = "f76ea978f0d42e021e98dc9239f8fc48"
HOST = "bodenbericht.de"
KEY_LOCATION = f"https://{HOST}/{INDEXNOW_KEY}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"

LANDING_DIR = Path(__file__).resolve().parents[1]
SITEMAP_PATH = LANDING_DIR / "sitemap.xml"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("index_now")


def parse_sitemap_urls(sitemap: Path) -> list[str]:
    """Return all <loc> URLs from a sitemap.xml."""
    if not sitemap.exists():
        log.error("Sitemap not found at %s", sitemap)
        return []
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    try:
        tree = ET.parse(sitemap)
    except ET.ParseError as exc:
        log.error("Sitemap parse error: %s", exc)
        return []
    return [el.text.strip() for el in tree.getroot().findall("sm:url/sm:loc", ns) if el.text]


def push_indexnow(urls: list[str], dry_run: bool = False) -> bool:
    """POST batch to IndexNow. Returns True on 200/202, False otherwise."""
    if not urls:
        log.warning("No URLs to push.")
        return False

    payload = {
        "host": HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls,
    }

    if dry_run:
        log.info("[DRY-RUN] Would POST %d URLs to %s", len(urls), ENDPOINT)
        for u in urls:
            log.info("  %s", u)
        return True

    import json
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Host": "api.indexnow.org",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            log.info(
                "IndexNow %s for %d URL(s) — host=%s",
                resp.status, len(urls), HOST,
            )
            return resp.status in (200, 202)
    except HTTPError as exc:
        log.warning("IndexNow HTTP %s: %s", exc.code, exc.read()[:200].decode("utf-8", "ignore"))
        return False
    except URLError as exc:
        log.warning("IndexNow network error: %s", exc.reason)
        return False


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "paths",
        nargs="*",
        help="Optional path-only URLs to push (e.g. /pilot). "
        "If omitted, all URLs from sitemap.xml are pushed.",
    )
    p.add_argument("--dry-run", action="store_true", help="Log only, do not send.")
    args = p.parse_args()

    if args.paths:
        urls = [
            f"https://{HOST}{path}" if path.startswith("/") else f"https://{HOST}/{path}"
            for path in args.paths
        ]
    else:
        urls = parse_sitemap_urls(SITEMAP_PATH)

    ok = push_indexnow(urls, dry_run=args.dry_run)
    # Best-effort: don't fail the deploy on IndexNow errors.
    return 0 if ok else 0


if __name__ == "__main__":
    sys.exit(main())
