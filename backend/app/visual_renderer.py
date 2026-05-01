"""SVG template renderer for the visuals payload.

Single render path for the 6 visualisation components plus any
auxiliary SVG fragments (teaser-wrapper, lock-overlay, etc.).

Usage
-----
::

    from app.visual_renderer import render_svg

    svg = render_svg("risk_dashboard", payload["components"]["risk_dashboard"])

The returned string is well-formed SVG that can be embedded inline in
HTML (the new Chrome-Headless render path) or written to disk for
preview. There is no PNG bridge — Chrome rasterises inline SVG itself.

Templates
---------
Templates live in ``backend/templates/visuals/*.svg.jinja2``. Each
component has one template named by its data-contract key. Templates
have access to:

- ``data`` — the component dict passed to ``render_svg``
- ``tokens`` — the parsed ``shared/visual_tokens.json``
- ``ampel(value_mm_per_year)`` — helper that returns the ampel band
  for an absolute velocity value in mm/yr
- ``fmt_signed(x, digits=1)`` — formats a number with explicit sign
  ("+1.4", "-0.3", "0")

Templates may ``{% include %}`` partial fragments (teaser-wrapper,
lock-icon, etc.) — Jinja resolves those relative to the templates
directory.
"""

from __future__ import annotations

import functools
import json
import logging
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_ROOT.parent

TEMPLATES_DIR = _BACKEND_ROOT / "templates" / "visuals"
TOKENS_PATH = _REPO_ROOT / "shared" / "visual_tokens.json"


# ---------------------------------------------------------------------------
# Token loading
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def load_tokens() -> dict[str, Any]:
    """Load and cache ``shared/visual_tokens.json``."""
    if not TOKENS_PATH.exists():
        raise FileNotFoundError(f"Visual tokens not found at {TOKENS_PATH}")
    return json.loads(TOKENS_PATH.read_text(encoding="utf-8"))


def reload_tokens() -> None:
    """Drop the cached tokens — useful for tests that mutate the file."""
    load_tokens.cache_clear()


# ---------------------------------------------------------------------------
# Template helpers (callable from Jinja)
# ---------------------------------------------------------------------------

def _ampel_band(value_mm_per_year: float | None) -> dict[str, Any]:
    """Return the ampel band for an absolute velocity value.

    Falls back to ``stabil`` when value is None — the template can
    decide whether that's appropriate or not.
    """
    tokens = load_tokens()
    bands = tokens["ampel"]
    if value_mm_per_year is None:
        return bands["stabil"]
    v = abs(float(value_mm_per_year))
    for key in ("stabil", "leicht", "moderat", "auffaellig", "erheblich", "kritisch"):
        band = bands[key]
        lo, hi = band["range_mm_per_year"]
        if lo <= v < hi:
            return band
    return bands["kritisch"]


def _fmt_signed(value: float | int | None, digits: int = 1) -> str:
    if value is None:
        return "—"
    n = float(value)
    if n == 0:
        return "0"
    return f"{n:+.{digits}f}"


def _fmt_int(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{int(round(float(value)))}"


def _fit(value: Any, max_chars: int) -> str:
    """Truncate a string to ``max_chars`` with an ellipsis. SVG <text>
    has no auto-wrap — long strings overflow their bounding box. This
    helper is the last-resort backstop for any user-visible text that
    flows into a fixed-width slot in a template."""
    if value is None:
        return "—"
    s = str(value)
    if len(s) <= max_chars:
        return s
    if max_chars <= 1:
        return s[:max_chars]
    return s[: max_chars - 1].rstrip(" ,;:.-—·") + "…"


def _grade_band(grade: str | None) -> dict[str, Any]:
    """Map A-E grade letter to an ampel-band dict for color use."""
    tokens = load_tokens()
    bands = tokens["ampel"]
    return {
        "A": bands["stabil"],
        "B": bands["leicht"],
        "C": bands["moderat"],
        "D": bands["auffaellig"],
        "E": bands["erheblich"],
    }.get((grade or "").upper(), {
        "color": "#888780",
        "label": "nicht bewertbar",
        "burland_class": 0,
    })


def _ampel_for_label(label: str | None) -> dict[str, Any]:
    """Look up an ampel band by its German label (e.g. 'leicht')."""
    tokens = load_tokens()
    for band in tokens["ampel"].values():
        if band["label"] == label:
            return band
    return tokens["ampel"]["stabil"]


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def _env() -> Environment:
    if not TEMPLATES_DIR.exists():
        raise FileNotFoundError(
            f"Visuals templates directory not found at {TEMPLATES_DIR}. "
            "Create it as part of V.1.5."
        )
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["xml", "svg"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals["ampel"] = _ampel_band
    env.globals["ampel_for_label"] = _ampel_for_label
    env.globals["grade_band"] = _grade_band
    env.globals["fmt_signed"] = _fmt_signed
    env.globals["fmt_int"] = _fmt_int
    env.globals["fit"] = _fit
    return env


def reload_env() -> None:
    _env.cache_clear()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_svg(name: str, data: dict[str, Any], **extra_context: Any) -> str:
    """Render the named SVG template with ``data``.

    ``name`` is the component key (e.g. ``"risk_dashboard"``,
    ``"property_context_map"``). The template file is resolved as
    ``<TEMPLATES_DIR>/<name>.svg.jinja2``.

    Additional Jinja variables can be passed via ``extra_context``.
    For example, the property-context-map template needs a ``map`` arg
    holding the pre-projected render context::

        render_svg("property_context_map", component, map=map_ctx)
    """
    template = _env().get_template(f"{name}.svg.jinja2")
    return template.render(data=data, tokens=load_tokens(), **extra_context)


_VIEWBOX_RE = re.compile(
    r'<svg[^>]*\bviewBox="\s*\d+\s+\d+\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*"',
    re.IGNORECASE,
)


def _extract_viewbox(svg: str) -> tuple[int, int]:
    """Pull the (width, height) from the outer <svg viewBox="0 0 W H">."""
    m = _VIEWBOX_RE.search(svg)
    if not m:
        return 680, 320
    return int(float(m.group(1))), int(float(m.group(2)))


def wrap_teaser(
    inner_svg: str,
    cta_text: str = "Premium-Inhalt",
    cta_url: str | None = None,
) -> str:
    """Wrap a Tier-2 SVG with the teaser blur + lock overlay.

    Used by the Free-report renderer to produce the verschwommene
    Vorschau described in SPEC §5. Premium-report skips this and
    embeds the SVG directly.
    """
    width, height = _extract_viewbox(inner_svg)
    template = _env().get_template("_teaser_wrapper.svg.jinja2")
    return template.render(
        data={},
        tokens=load_tokens(),
        inner_svg=inner_svg,
        inner_width=width,
        inner_height=height,
        cta_text=cta_text,
        cta_url=cta_url,
    )
