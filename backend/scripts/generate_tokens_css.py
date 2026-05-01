"""Generate ``backend/static/css/tokens.css`` from
``shared/visual_tokens.json``.

Single source of truth: the JSON file. This script flattens the
relevant tokens into CSS custom properties so HTML templates and CSS
files can reference them by name without hardcoding hex values.

Run::

    python -m backend.scripts.generate_tokens_css

or as part of the build/deploy pipeline. The script is idempotent —
it overwrites the output file each run.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOKENS_JSON = REPO_ROOT / "shared" / "visual_tokens.json"
OUT_CSS = REPO_ROOT / "backend" / "static" / "css" / "tokens.css"


def _flatten_to_vars(tokens: dict) -> list[tuple[str, str]]:
    """Pick the values we want exposed as CSS custom properties."""
    vars_: list[tuple[str, str]] = []

    # Ampel colors
    for key, band in tokens["ampel"].items():
        vars_.append((f"--ampel-{key}", band["color"]))
    vars_.append(("--ampel-edge", tokens["ampel_edge"]["color"]))

    # Accent
    vars_.append(("--accent-own-property", tokens["accent"]["own_property"]["color"]))
    vars_.append(("--accent-trend", tokens["accent"]["trend_line"]["color"]))
    vars_.append(("--accent-psi-motion", tokens["accent"]["psi_motion"]["color"]))

    # Structural
    for key, item in tokens["structural"].items():
        vars_.append((f"--structural-{key}", item["color"]))

    # Typography
    typo = tokens["typography"]
    vars_.append(("--font-sans", typo["font_family_sans"]))
    vars_.append(("--font-display", typo["font_family_display"]))
    vars_.append(("--font-mono", typo["font_family_mono"]))
    for key, px in typo["scale_px"].items():
        vars_.append((f"--fs-{key.replace('_', '-')}", f"{px}px"))

    # Layout
    vars_.append(("--viewbox-width", f"{tokens['layout']['viewbox_width_px']}px"))
    vars_.append(("--padding", f"{tokens['layout']['padding_px']}px"))

    # Report design — Premium (Cozy)
    prem = tokens["report_design"]["premium"]
    vars_.append(("--premium-bg", prem["background"]))
    vars_.append(("--premium-fg", prem["foreground"]))
    vars_.append(("--premium-accent", prem["accent"]))
    vars_.append(("--premium-border", prem["border"]))

    # Report design — Free (bodenbericht)
    free = tokens["report_design"]["free"]
    vars_.append(("--free-bg", free["background"]))
    vars_.append(("--free-accent", free["accent"]))

    # Tier blur
    vars_.append(("--teaser-blur", tokens["tier_blur"]["free_teaser_filter"]))
    vars_.append(("--teaser-opacity", str(tokens["tier_blur"]["free_teaser_opacity"])))

    return vars_


def render_css(tokens: dict) -> str:
    lines = [
        "/* Auto-generated from shared/visual_tokens.json by",
        " * backend/scripts/generate_tokens_css.py — DO NOT EDIT BY HAND.",
        " * Re-run the generator after changing the JSON.",
        " */",
        "",
        ":root {",
    ]
    for name, value in _flatten_to_vars(tokens):
        lines.append(f"  {name}: {value};")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    if not TOKENS_JSON.exists():
        raise SystemExit(f"Tokens JSON not found: {TOKENS_JSON}")
    tokens = json.loads(TOKENS_JSON.read_text(encoding="utf-8"))
    css = render_css(tokens)
    OUT_CSS.parent.mkdir(parents=True, exist_ok=True)
    OUT_CSS.write_text(css, encoding="utf-8")
    print(f"Wrote {OUT_CSS} ({len(css)} chars, "
          f"{len(_flatten_to_vars(tokens))} variables)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
