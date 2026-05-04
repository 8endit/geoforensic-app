#!/usr/bin/env python3
"""Validate structural integrity of staged HTML files.

Catches the failure mode behind the 2026-05-04 footer-bug: a Regex-Sweep
über landing/wissen/* ersetzte `<footer ` durch ein SOH-Steuerzeichen
(\\x01) und kippte gleichzeitig `text-gray-300` → `text-gray-500` im
Footer-Block. Browser sind tolerant genug dass sowas visuell nicht
auffällt — bis zur nächsten Lighthouse-Runde oder bis ein
HTML-Validator drauf läuft.

Checks pro staged .html:
  - Keine Control-Bytes 0x00-0x08, 0x0b, 0x0c, 0x0e-0x1f (Tab/LF/CR
    sind erlaubt)
  - <footer>/</footer>, <header>/</header>, <main>/</main>,
    <body>/</body>, <html>/</html> sind balanced

Install lokal:
  ln -sf ../../scripts/pre-commit-html-check.py .git/hooks/pre-commit
  chmod +x scripts/pre-commit-html-check.py

Bypass (only for emergencies):
  git commit --no-verify

Auch via .github/workflows/html-integrity.yml als CI-Check, damit's
auch dann fängt wenn jemand den Hook lokal nicht installiert hat.
"""
from __future__ import annotations

import re
import subprocess
import sys

CONTROL_BYTES = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]")
HTML_COMMENT = re.compile(rb"<!--.*?-->", re.DOTALL)

# Major structural tags — open/close mismatch is always a bug for these
# (HTML5 has no self-closing form for any of them).
BALANCED_TAGS = ("html", "body", "header", "footer", "main")


def staged_html_files() -> list[str]:
    """Return paths to staged .html/.htm files (added/copied/modified)."""
    out = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        text=True,
    )
    return [
        line
        for line in out.splitlines()
        if line.endswith((".html", ".htm"))
    ]


def line_of_offset(data: bytes, offset: int) -> int:
    return data.count(b"\n", 0, offset) + 1


def check_file(path: str) -> list[str]:
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except FileNotFoundError:
        return []  # File deleted — skip

    errors: list[str] = []

    # Control bytes — report first occurrence, since one such byte
    # usually means the whole file came out of a buggy sweep.
    cb_match = CONTROL_BYTES.search(data)
    if cb_match:
        byte_hex = data[cb_match.start():cb_match.start() + 1].hex()
        errors.append(
            f"{path}: control byte 0x{byte_hex} at offset "
            f"{cb_match.start()} (line ~{line_of_offset(data, cb_match.start())})"
        )

    # Tag balance — strip comments first so commented-out tags don't count.
    cleaned = HTML_COMMENT.sub(b"", data)
    for tag in BALANCED_TAGS:
        tag_b = tag.encode()
        opens = len(re.findall(rb"<" + tag_b + rb"\b[^>]*>", cleaned))
        closes = len(re.findall(rb"</" + tag_b + rb"\s*>", cleaned))
        if opens != closes:
            errors.append(
                f"{path}: <{tag}> open={opens} close={closes} (mismatch)"
            )

    return errors


def main() -> int:
    files = staged_html_files()
    if not files:
        return 0

    all_errors: list[str] = []
    for f in files:
        all_errors.extend(check_file(f))

    if not all_errors:
        return 0

    print("HTML structural integrity check FAILED:", file=sys.stderr)
    for e in all_errors:
        print(f"  - {e}", file=sys.stderr)
    print(
        "\nFix the issues above and re-stage.\n"
        "Bypass only in emergencies: git commit --no-verify",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
