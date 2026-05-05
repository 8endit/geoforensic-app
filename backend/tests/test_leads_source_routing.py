"""Source-routing tests for /api/leads.

Deny-by-default: nur Stripe-flow Sources lösen den Vollbericht aus,
alles andere fällt durch auf Teaser. Jeder neue Source-String muss
explizit in PAID_SOURCES aufgenommen werden, sonst landet er
automatisch im sicheren Teaser-Pfad.

Vorher gab's eine pilot-vollbericht Source (kostenloser Vollbericht
für Pilot-Tester) — entfernt 2026-05-05 weil redundant mit EARLY50-
Coupon und widersprüchlich zur Discount-Strategie. Discount für die
ersten 50 läuft jetzt ausschließlich über den EARLY50-Coupon im
Stripe-Path (siehe routers/payments.py).

Implementation note: the test parses PAID_SOURCES out of the source file
via ast instead of importing it, because importing app.routers.leads
pulls in the full FastAPI/SQLAlchemy/redis stack which is overkill for
a constant assertion.
"""

import ast
from pathlib import Path

import pytest

LEADS_PATH = Path(__file__).resolve().parents[1] / "app" / "routers" / "leads.py"


@pytest.fixture(scope="module")
def paid_sources() -> set[str]:
    """Extract the PAID_SOURCES set literal from leads.py via ast."""
    tree = ast.parse(LEADS_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "PAID_SOURCES":
                    return set(ast.literal_eval(node.value))
    raise AssertionError("PAID_SOURCES not found in leads.py")


def test_existing_paid_sources_still_route_to_full_report(paid_sources):
    """Stripe/checkout sources stay whitelisted."""
    for src in ("paid", "checkout", "stripe"):
        assert src in paid_sources


def test_pilot_vollbericht_was_removed(paid_sources):
    """Pilot-Free-Path is gone; first-50 = EARLY50 discount via Stripe."""
    assert "pilot-vollbericht" not in paid_sources


@pytest.mark.parametrize(
    "src",
    [
        "quiz",                # Quiz funnel
        "landing",             # Landing direct form (legacy)
        "hero_direct",         # Hero inline form
        "landing_direct",      # Inline CTA form
        "premium-waitlist",    # Email-only waitlist (no address)
        "pilot",               # Typo variant — must not accidentally match
        "pilot-vollbericht",   # Removed source must not re-enter
        "vollbericht",         # Naked source name
        "",                    # Empty string
        "PILOT-VOLLBERICHT",   # Case mismatch
    ],
)
def test_unknown_sources_fall_through_to_teaser(paid_sources, src):
    """Deny-by-default — anything not explicitly listed is a teaser."""
    assert src not in paid_sources, (
        f"Source {src!r} unexpectedly routes to full report. "
        "Add to PAID_SOURCES deliberately or fix the test."
    )


def test_paid_sources_set_is_minimal(paid_sources):
    """Sanity check that we did not accidentally widen the whitelist."""
    assert paid_sources == {"paid", "checkout", "stripe"}
