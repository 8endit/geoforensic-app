"""Render HTML string to PDF bytes.

Strategy:
1. Chrome/Chromium headless (best quality, handles CSS/SVG perfectly)
2. WeasyPrint fallback (good quality, needs GTK libs)
3. Return HTML as-is if neither available (email as HTML attachment)

Chrome headless is preferred because it renders inline SVG charts correctly
and matches what the user sees in the browser.
"""

import logging
import os
import shutil
import subprocess
import tempfile

logger = logging.getLogger(__name__)

# Chrome/Chromium binary paths to try
_CHROME_PATHS = [
    os.getenv("CHROME_BIN", ""),
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
]


def _find_chrome() -> str | None:
    for path in _CHROME_PATHS:
        if path and shutil.which(path):
            return path
        if path and os.path.isfile(path):
            return path
    return None


def html_to_pdf(html: str) -> bytes | None:
    """Convert HTML string to PDF bytes. Returns None on failure."""
    # Strategy 1: Chrome headless
    chrome = _find_chrome()
    if chrome:
        try:
            return _chrome_pdf(chrome, html)
        except Exception:
            logger.warning("Chrome PDF rendering failed, trying WeasyPrint", exc_info=True)

    # Strategy 2: WeasyPrint
    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except Exception:
        logger.warning("WeasyPrint not available or failed", exc_info=True)

    # Strategy 3: Return None (caller decides what to do)
    logger.error("No PDF renderer available (Chrome + WeasyPrint both failed)")
    return None


def _chrome_pdf(chrome_path: str, html: str) -> bytes:
    """Use Chrome headless to render HTML to PDF."""
    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = os.path.join(tmpdir, "report.html")
        pdf_path = os.path.join(tmpdir, "report.pdf")

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        cmd = [
            chrome_path,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-software-rasterizer",
            "--disable-dev-shm-usage",
            "--run-all-compositor-stages-before-draw",
            "--print-to-pdf=" + pdf_path,
            "--no-pdf-header-footer",
            "--print-to-pdf-no-header",
            "file:///" + html_path.replace("\\", "/"),
        ]

        # 30 s war zu knapp für Vollberichte mit ~20 inline-SVGs +
        # Embedded-Fonts; Chrome wurde dann mit SIGTERM gekillt und
        # _chrome_pdf raised RuntimeError → Vollbericht still failed.
        # 120 s ist großzügig, die echte Wall-Time liegt typisch 25-60 s.
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=120,
        )

        if not os.path.exists(pdf_path):
            raise RuntimeError(
                f"Chrome did not produce PDF. Exit code: {result.returncode}. "
                f"stderr: {result.stderr.decode('utf-8', errors='replace')[:500]}"
            )

        with open(pdf_path, "rb") as f:
            return f.read()
