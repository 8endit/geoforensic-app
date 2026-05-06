"""Test fuer den Source-zu-Nutzung-Autofill in routers/leads.py.

Vor 2026-05-06 war die Admin-Dashboard-Spalte "Nutzung" nur fuer
Quiz-Leads gefuellt — Persona-Page-Leads (landing_kaeufer,
landing_bautraeger, etc.) und Direct-Buy-Leads (hero_direct,
direct-purchase, paid) hatten leere Felder. Source-zu-Nutzung-Mapping
fuellt das implizit aus dem source-Feld auf, ohne den Lead-Form um
ein Pflicht-Dropdown zu erweitern (Conversion-Risiko).

Wir testen das Mapping isoliert via ast-Inspektion — Import von
app.routers.leads ist heavyweight (FastAPI/SQLAlchemy).
"""

import ast
import re
from pathlib import Path

import pytest

LEADS_PATH = Path(__file__).resolve().parents[1] / "app" / "routers" / "leads.py"


@pytest.fixture(scope="module")
def src_to_nutzung() -> dict[str, str]:
    """Extract _src_to_nutzung dict literal from leads.py via ast."""
    text = LEADS_PATH.read_text(encoding="utf-8")
    tree = ast.parse(text)

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "_src_to_nutzung":
                    if isinstance(node.value, ast.Dict):
                        out = {}
                        for k, v in zip(node.value.keys, node.value.values):
                            if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                                out[k.value] = v.value
                        return out
    pytest.fail("_src_to_nutzung not found in leads.py")


@pytest.mark.parametrize(
    "source, expected",
    [
        ("landing_kaeufer", "Hauskauf"),
        ("landing_bautraeger", "Bau / Bauträger"),
        ("landing_garten", "Garten / Eigenheim"),
        ("landing_landwirte", "Landwirtschaft"),
        ("hero_direct", "Direktkauf (Hero-Form)"),
        ("landing_direct", "Direktkauf (Premium-Form)"),
        ("live-check", "Adresse-Check (Hauptseite)"),
        ("direct-purchase", "Direktkauf"),
        ("paid", "Direktkauf"),
        ("checkout", "Direktkauf"),
        ("stripe", "Direktkauf"),
    ],
)
def test_source_to_nutzung_mapping(src_to_nutzung: dict, source: str, expected: str) -> None:
    assert src_to_nutzung.get(source) == expected, (
        f"Source '{source}' soll '{expected}' liefern, hat aber: {src_to_nutzung.get(source)!r}"
    )


def test_quiz_source_not_overridden(src_to_nutzung: dict) -> None:
    """Quiz-Leads behalten ihre Quiz-Antwort — kein Override aus dem Mapping."""
    # Quiz selbst muss NICHT im Mapping sein (Quiz setzt nutzung explizit
    # aus answer[0]). Wenn ein Quiz-Lead mit leerem nutzung kaeme, ist das
    # ein Quiz-Bug, nicht ein Routing-Problem.
    assert "quiz" not in src_to_nutzung


def test_premium_waitlist_not_overridden(src_to_nutzung: dict) -> None:
    """premium-waitlist ist ein DOI-Lead ohne Adresse — keine Nutzung implizit."""
    assert "premium-waitlist" not in src_to_nutzung


def test_autofill_only_when_empty() -> None:
    """Code-Pfad muss Quiz-Antwort respektieren (nur fillen wenn leer)."""
    text = LEADS_PATH.read_text(encoding="utf-8")
    # Pruefen dass die Bedingung "if not answers_with_address.get('nutzung')"
    # vor dem Setzen steht — sonst koennte das Mapping ein Quiz-Antwort
    # ueberschreiben.
    assert re.search(
        r'if\s+not\s+answers_with_address\.get\(\s*[\'"]nutzung[\'"]\s*\)',
        text,
    ), "Autofill muss konditional auf leeres nutzung-Feld sein"
