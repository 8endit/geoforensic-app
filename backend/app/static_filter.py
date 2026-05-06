"""Defense-in-Depth-Filter für den landing/-Static-Mount.

PRIMARY DEFENSE läuft in Caddy (siehe scripts/Caddyfile.proposed),
weil Caddy die statischen Files direkt aus /opt/bodenbericht/landing
serviert und nur /api/* + /r/* an FastAPI weiterreicht. Dieser
Backend-Filter ist redundant zum Caddy-Block — bleibt aber als
Safety-Net falls jemand die Caddy-Config je vereinfacht oder
FastAPI direkt exponiert wird (z.B. lokal ohne Caddy davor).

Eingeführt 2026-05-05 nach Web-Exposure-Audit, Caddy-Spiegelung
2026-05-06 nach Live-Test (Backend-Filter wurde nie getriggert,
Caddy-Vorblock fehlte).
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
