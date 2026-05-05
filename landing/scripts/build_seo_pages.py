#!/usr/bin/env python3
"""SEO-Long-Tail-Stadt-Pages Generator.

Liest landing/scripts/seo_pages.json + landing/scripts/seo_template.html.jinja2
und schreibt für jeden Eintrag in 'pages' eine HTML-Page nach
landing/orte/<thema_slug>-<stadt_slug>.html.

Eingeführt 2026-05-05 für Sprint D14 (Marketing-Kanal-Aufbau): statt
generischer index.html-Hauptseite gezielt auf Long-Tail-Suchanfragen
zugeschnittene Pages für die 30 wichtigsten Städte mit Bergbau-/
Industrie-/Hochwasser-/Funderlabel-Bezug.

Aufruf vom Repo-Root:
    python landing/scripts/build_seo_pages.py            # alle Pages
    python landing/scripts/build_seo_pages.py --dry-run  # nur listen
    python landing/scripts/build_seo_pages.py --sitemap  # zusätzlich
                                                          # sitemap-Snippet

Die generierten Pages werden NICHT eingecheckt (.gitignore-Eintrag bei
Bedarf). Stattdessen läuft das Skript bei jedem Deploy einmal —
analog zum tailwind-Build.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError as e:
    sys.stderr.write(f"jinja2 fehlt — `pip install jinja2`\n{e}\n")
    sys.exit(1)


SCRIPTS_DIR = Path(__file__).resolve().parent
LANDING_DIR = SCRIPTS_DIR.parent
DATA_FILE = SCRIPTS_DIR / "seo_pages.json"
TEMPLATE_FILE = "seo_template.html.jinja2"
OUTPUT_DIR = LANDING_DIR / "orte"


def load_pages() -> list[dict]:
    if not DATA_FILE.exists():
        sys.stderr.write(f"Daten-File nicht gefunden: {DATA_FILE}\n")
        sys.exit(1)
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    pages = [p for p in data.get("pages", []) if not p.get("_skip")]
    if not pages:
        sys.stderr.write("Keine 'pages' im JSON definiert.\n")
        sys.exit(1)
    return pages


def render(pages: list[dict], dry_run: bool = False) -> list[Path]:
    env = Environment(
        loader=FileSystemLoader(str(SCRIPTS_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tmpl = env.get_template(TEMPLATE_FILE)

    if not dry_run:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for page in pages:
        slug = f"{page['thema_slug']}-{page['stadt_slug']}"
        out = OUTPUT_DIR / f"{slug}.html"
        if dry_run:
            print(f"  [dry-run] would write {out.relative_to(LANDING_DIR)}")
        else:
            html = tmpl.render(**page)
            out.write_text(html, encoding="utf-8")
            print(f"  wrote {out.relative_to(LANDING_DIR)} ({len(html)} bytes)")
        written.append(out)
    return written


def sitemap_snippet(pages: list[dict]) -> str:
    """Snippet für sitemap.xml zum manuellen Einkleben.

    Wir patchen die echte sitemap.xml NICHT automatisch, weil sie
    handgepflegt ist — der Operator entscheidet, ob neu generierte
    Pages in den nächsten Sitemap-Push gehen.
    """
    today = date.today().isoformat()
    lines = []
    for page in pages:
        slug = f"{page['thema_slug']}-{page['stadt_slug']}"
        url = f"https://bodenbericht.de/orte/{slug}.html"
        lines.append("  <url>")
        lines.append(f"    <loc>{url}</loc>")
        lines.append(f"    <lastmod>{today}</lastmod>")
        lines.append("    <changefreq>monthly</changefreq>")
        lines.append("    <priority>0.5</priority>")
        lines.append("  </url>")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Nicht schreiben, nur listen")
    parser.add_argument("--sitemap", action="store_true", help="Sitemap-Snippet auf stdout drucken")
    args = parser.parse_args()

    pages = load_pages()
    print(f"Loaded {len(pages)} page(s) from {DATA_FILE.name}")
    render(pages, dry_run=args.dry_run)

    if args.sitemap:
        print()
        print("=" * 60)
        print("Sitemap-Snippet zum Einkleben in landing/sitemap.xml:")
        print("=" * 60)
        print(sitemap_snippet(pages))

    return 0


if __name__ == "__main__":
    sys.exit(main())
