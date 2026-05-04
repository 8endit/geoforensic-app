#!/usr/bin/env python3
"""Generate sitemap.xml with <lastmod> from each HTML file's mtime.

Run from `landing/` (or via `python landing/scripts/build_sitemap.py`).
Overwrites `landing/sitemap.xml`. Run on every deploy to keep lastmod fresh.

The URL list + priority/changefreq lives here (instead of being scraped from
the filesystem) so we don't accidentally publish admin.html, 404.html, or
work-in-progress files.
"""
from __future__ import annotations

import datetime as dt
import os
import sys

BASE = "https://bodenbericht.de"

# (relative path on disk, sitemap loc, changefreq, priority)
URLS = [
    ("index.html",                                      f"{BASE}/",                                            "weekly",  "1.0"),
    ("quiz.html",                                       f"{BASE}/quiz.html",                                   "monthly", "0.9"),
    ("fuer-immobilienkaeufer.html",                     f"{BASE}/fuer-immobilienkaeufer.html",                 "monthly", "0.9"),
    ("fuer-gartenbesitzer.html",                        f"{BASE}/fuer-gartenbesitzer.html",                    "monthly", "0.8"),
    ("fuer-bautraeger.html",                            f"{BASE}/fuer-bautraeger.html",                        "monthly", "0.8"),
    ("fuer-landwirte.html",                             f"{BASE}/fuer-landwirte.html",                         "monthly", "0.7"),
    ("muster-bericht.html",                             f"{BASE}/muster-bericht.html",                         "monthly", "0.7"),
    ("datenquellen.html",                               f"{BASE}/datenquellen.html",                           "monthly", "0.7"),
    ("wissen/index.html",                               f"{BASE}/wissen/",                                     "monthly", "0.6"),
    ("wissen/altlast.html",                             f"{BASE}/wissen/altlast.html",                         "monthly", "0.6"),
    ("wissen/setzung-vs-hebung.html",                   f"{BASE}/wissen/setzung-vs-hebung.html",               "monthly", "0.6"),
    ("wissen/eu-bodenrichtlinie.html",                  f"{BASE}/wissen/eu-bodenrichtlinie.html",              "monthly", "0.6"),
    ("wissen/schwermetalle-im-boden.html",              f"{BASE}/wissen/schwermetalle-im-boden.html",          "monthly", "0.6"),
    ("wissen/insar-egms.html",                          f"{BASE}/wissen/insar-egms.html",                      "monthly", "0.6"),
    ("wissen/hochwasser-risikoklasse.html",             f"{BASE}/wissen/hochwasser-risikoklasse.html",         "monthly", "0.6"),
    ("wissen/bbodschv.html",                            f"{BASE}/wissen/bbodschv.html",                        "monthly", "0.6"),
    ("wissen/erosion-rusle.html",                       f"{BASE}/wissen/erosion-rusle.html",                   "monthly", "0.6"),
    ("impressum.html",                                  f"{BASE}/impressum.html",                              "yearly",  "0.3"),
    ("datenschutz.html",                                f"{BASE}/datenschutz.html",                            "yearly",  "0.3"),
    ("widerruf.html",                                   f"{BASE}/widerruf.html",                               "yearly",  "0.2"),
]


def lastmod(path: str) -> str:
    try:
        mtime = os.stat(path).st_mtime
    except FileNotFoundError:
        return dt.date.today().isoformat()
    return dt.datetime.fromtimestamp(mtime, tz=dt.timezone.utc).date().isoformat()


def build(landing_dir: str) -> str:
    out = ['<?xml version="1.0" encoding="UTF-8"?>']
    out.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for relpath, loc, freq, prio in URLS:
        full = os.path.join(landing_dir, relpath)
        out.append("  <url>")
        out.append(f"    <loc>{loc}</loc>")
        out.append(f"    <lastmod>{lastmod(full)}</lastmod>")
        out.append(f"    <changefreq>{freq}</changefreq>")
        out.append(f"    <priority>{prio}</priority>")
        out.append("  </url>")
    out.append("</urlset>")
    out.append("")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    landing_dir = os.path.abspath(os.path.join(here, ".."))
    sitemap_path = os.path.join(landing_dir, "sitemap.xml")
    content = build(landing_dir)
    with open(sitemap_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"Wrote {sitemap_path} ({len(URLS)} URLs)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
