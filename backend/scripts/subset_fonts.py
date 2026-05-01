"""Subset display + mono fonts to a minimal Latin glyph set.

Why subset?
-----------
The full Sentient and Geist Mono fonts cover thousands of glyphs we
will never use in a German/Dutch property report. Subsetting to just
Latin + the symbols we need cuts the embed payload from ~200 KB per
weight down to ~30 KB and keeps the inline ``data:`` URI in the
generated PDF small (V.4 acceptance: PDF < 1.5 MB total).

Output
------
``backend/static/fonts/`` gets the subset woff2 files. The HTML
templates reference them via ``@font-face`` with a ``data:`` URI so
Chrome-Headless does not need to fetch anything during render.

Sources (committed under ``backend/static/fonts/source/``):
  - Sentient-Extralight.woff       (Indian Type Foundry, free for commercial)
  - Sentient-LightItalic.woff
  - GeistMono-Regular.woff2        (Vercel, OFL)
  - GeistMono-Medium.woff2

Run::

    python -m backend.scripts.subset_fonts

The script is idempotent and safe to run from any directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = REPO_ROOT / "backend" / "static" / "fonts" / "source"
OUT_DIR = REPO_ROOT / "backend" / "static" / "fonts"

# Glyph set: ASCII printable + German umlauts + Dutch IJ + selected
# typographic symbols and units that appear in the reports.
GLYPHS = (
    # Printable ASCII (space through tilde) — covered by the unicode range
    list(range(0x0020, 0x007F))
    # German + Western European
    + [0x00A0, 0x00A2, 0x00A3, 0x00A5, 0x00A7, 0x00A9, 0x00AB, 0x00AE,
       0x00B0, 0x00B1, 0x00B2, 0x00B3, 0x00B4, 0x00B5, 0x00B6, 0x00B7,
       0x00BB, 0x00BC, 0x00BD, 0x00BE]
    # Latin-1 supplement letters with diacritics (covers ä, ö, ü, ß, é, è, …)
    + list(range(0x00C0, 0x0100))
    # Common European punctuation: en/em dash, smart quotes, ellipsis, etc.
    + [0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015,
       0x2018, 0x2019, 0x201A, 0x201C, 0x201D, 0x201E,
       0x2022, 0x2026, 0x2030, 0x2032, 0x2033,
       0x2039, 0x203A]
    # Math + arrows used in dashboard and radar
    + [0x00D7, 0x00F7, 0x2190, 0x2191, 0x2192, 0x2193, 0x2194,
       0x2212, 0x2248, 0x2260, 0x2264, 0x2265]
    # Currency
    + [0x20AC]  # €
)


def _subset_one(src: Path, dst: Path, label: str) -> None:
    from fontTools.subset import Subsetter, load_font, save_font, Options

    options = Options()
    options.flavor = "woff2"
    options.layout_features = "*"  # keep ligatures, kerning, etc.
    options.name_IDs = ["*"]
    options.glyph_names = False
    options.legacy_kern = False
    options.notdef_outline = True
    options.recommended_glyphs = True
    options.recalc_bounds = True
    options.recalc_timestamp = False

    font = load_font(str(src), options)
    subsetter = Subsetter(options=options)
    unicodes = list(set(GLYPHS))
    subsetter.populate(unicodes=unicodes)
    subsetter.subset(font)
    dst.parent.mkdir(parents=True, exist_ok=True)
    save_font(font, str(dst), options)
    src_kb = src.stat().st_size / 1024
    dst_kb = dst.stat().st_size / 1024
    print(f"  {label:30s} {src_kb:6.1f} KB -> {dst_kb:6.1f} KB  ({dst.name})")


def main() -> int:
    if not SOURCE_DIR.exists():
        print(f"Source font directory missing: {SOURCE_DIR}", file=sys.stderr)
        return 1

    pairs: list[tuple[str, str, str]] = [
        # (source filename, output filename, human label)
        ("Sentient-Extralight.woff",   "sentient-extralight.woff2",  "Sentient Extralight"),
        ("Sentient-LightItalic.woff",  "sentient-lightitalic.woff2", "Sentient Light Italic"),
        ("GeistMono-Regular.woff2",    "geist-mono-regular.woff2",   "Geist Mono Regular"),
        ("GeistMono-Medium.woff2",     "geist-mono-medium.woff2",    "Geist Mono Medium"),
    ]

    print(f"Subsetting {len(pairs)} font files -> {OUT_DIR}")
    for src_name, dst_name, label in pairs:
        src = SOURCE_DIR / src_name
        dst = OUT_DIR / dst_name
        if not src.exists():
            print(f"  SKIP {label}: source missing ({src_name})")
            continue
        _subset_one(src, dst, label)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
