"""Source-routing tests for /api/leads.

These guard A.8 from the SEO-Branding-Rollout-Plan: the landing form
"Premium-Vorab-Anfrage" emits source="pilot-vollbericht" and MUST yield
the Vollbericht (is_teaser=False), while every other source falls
through to the teaser. This is also where future flow additions get
caught — every new source string defaults to teaser unless it gets
explicitly added to PAID_SOURCES.

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


def test_pilot_vollbericht_is_paid_source(paid_sources):
    """The pilot landing form must route to the full report."""
    assert "pilot-vollbericht" in paid_sources


def test_existing_paid_sources_still_route_to_full_report(paid_sources):
    """Stripe/checkout sources stay whitelisted after the pilot addition."""
    for src in ("paid", "checkout", "stripe"):
        assert src in paid_sources


@pytest.mark.parametrize(
    "src",
    [
        "quiz",                # Quiz funnel
        "landing",             # Landing direct form (legacy)
        "hero_direct",         # Hero inline form
        "landing_direct",      # Inline CTA form
        "premium-waitlist",    # Email-only waitlist (no address)
        "pilot",               # Typo variant — must not accidentally match
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
    assert paid_sources == {"paid", "checkout", "stripe", "pilot-vollbericht"}
