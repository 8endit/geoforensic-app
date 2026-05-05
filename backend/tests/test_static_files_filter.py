"""Tests für den Defense-in-Depth-Filter im landing/-Static-Mount.

Der Filter wurde 2026-05-05 eingebaut nachdem `landing/build.ps1` und
`landing/build_brand_assets.py` über die Public-URL HTTP 200 lieferten.
Source-/Tooling-Endungen + Dotfiles sollen blockiert werden, normale
HTML/PNG/SVG-Inhalte und der RFC-8615-`.well-known/`-Pfad nicht.
"""

from __future__ import annotations

import pytest

from app.static_filter import is_blocked_static_path


@pytest.mark.parametrize(
    "path",
    [
        # Backend-/Tooling-Endungen
        "build.ps1",
        "build_brand_assets.py",
        "scripts/build_landing_visuals.py",
        "scripts/build_sitemap.py",
        "scripts/index_now.py",
        "tailwindcss.exe",
        "tools/install.sh",
        "deploy.bash",
        "config.ps1xml",
        # Dotfiles auf jeder Tiefe
        ".env",
        ".env.local",
        ".git/HEAD",
        ".gitignore",
        ".DS_Store",
        "subdir/.env",
        "klaro/.gitkeep",
        # Auch mit führendem Slash
        "/.env",
        "/build.ps1",
        # Tooling-Bereich landing/scripts/ kategorisch blockieren —
        # SEO-Generator-Setup ab 2026-05-05
        "scripts/seo_pages.json",
        "scripts/seo_template.html.jinja2",
        "scripts/README_seo.md",
        "scripts/anything-here",
    ],
)
def test_blocked_paths_are_rejected(path: str) -> None:
    assert is_blocked_static_path(path) is True, f"Should block: {path}"


@pytest.mark.parametrize(
    "path",
    [
        # Reguläre Web-Inhalte
        "index.html",
        "muster-bericht.html",
        "fuer-immobilienkaeufer.html",
        "datenquellen.html",
        "wissen/eu-bodenrichtlinie.html",
        "orte/bodenbewegung-bochum.html",
        "orte/funderingslabel-amsterdam.html",
        "images/logo-horizontal.png",
        "static/visuals/01_risk_dashboard.svg",
        "tailwind.css",
        "favicon.ico",
        "klaro/klaro.js",
        "fonts/inter-400.woff2",
        "robots.txt",
        "sitemap.xml",
        # RFC 8615 well-known — Let's Encrypt etc.
        ".well-known/acme-challenge/abc123",
        ".well-known/security.txt",
        ".well-known/apple-app-site-association",
        # Auch mit führendem Slash
        "/index.html",
        "/.well-known/acme-challenge/x",
    ],
)
def test_legitimate_paths_pass_through(path: str) -> None:
    assert is_blocked_static_path(path) is False, f"Should allow: {path}"


def test_case_insensitivity() -> None:
    """Ein Angreifer könnte versuchen, Endung großzuschreiben."""
    assert is_blocked_static_path("Build.PS1") is True
    assert is_blocked_static_path("SETUP.SH") is True
    assert is_blocked_static_path(".ENV") is True


def test_well_known_subpath_is_strict() -> None:
    """`.well-known/` muss am Anfang stehen — keine Tarnung mit Dotfile davor."""
    assert is_blocked_static_path(".badmask/.well-known/secret") is True
    assert is_blocked_static_path(".well-known.evil/test") is True
