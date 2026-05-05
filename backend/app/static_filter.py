"""Defense-in-Depth-Filter für den landing/-Static-Mount.

Build- und Source-Skripte in landing/scripts/*.py + ein historischer
landing/build.ps1 waren über die Domain abrufbar (HTTP 200), weil das
gesamte landing/-Tree unter "/" gemountet wird. Files mit Backend/Source-/
Tooling-Endungen gehören nicht ins Web und werden zentral blockiert.

Eingeführt 2026-05-05 nach Web-Exposure-Audit.
"""

from __future__ import annotations

_BLOCKED_STATIC_SUFFIXES = (".py", ".ps1", ".exe", ".sh", ".bash", ".ps1xml")

# Kategorisch geblockte Pfad-Praefixe: das sind interne Tooling-Bereiche
# unter landing/, die niemals oeffentlich sein sollen — egal welche
# Datei-Endung (Templates .jinja2, Daten .json, Doku .md, Build-Skripte).
_BLOCKED_PATH_PREFIXES = ("scripts/",)


def is_blocked_static_path(path: str) -> bool:
    """Block backend/source/tooling files and stray dotfiles served via the landing mount.

    Whitelist .well-known/ because Let's Encrypt's HTTP-01 challenge
    and other RFC 8615 well-known URIs (e.g. apple-app-site-assoc,
    security.txt) live there. Everything else with a dot-prefixed
    segment is treated as a leak attempt (.git/, .env, .DS_Store, …).
    """
    lower = path.lower().lstrip("/")
    if lower.startswith(".well-known/"):
        return False
    if lower.startswith(_BLOCKED_PATH_PREFIXES):
        return True
    if lower.endswith(_BLOCKED_STATIC_SUFFIXES):
        return True
    return any(seg.startswith(".") for seg in lower.split("/") if seg)
