"""Shared types + key-constants used across the pipeline.

Diese Datei ist die single source of truth für:
- die genauen Keys die SoilDataLoader.query_full_profile() rausgibt
- die Pill-Status-Strings die das Backend liefert (vs CSS-Aliase)

Hintergrund: Tippfehler bei dict-Keys waren bisher silent (None statt
Crash). Echtes Beispiel 2026-05-05: `full_report.py` machte
`get("imperviousness")` aber der Key heißt `imperviousness_pct` →
Versiegelung war im Vollbericht monatelang n/a, niemand hat's gemerkt.
Mit dieser Datei + safe_pluck() unten loggt der Code WARNUNG sobald
ein nicht-deklarierter Key gelesen wird.
"""

from __future__ import annotations

import logging
from typing import Any, Literal, TypedDict

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────
# SoilProfile — Output von SoilDataLoader.query_full_profile()
# ──────────────────────────────────────────────────────────────────────────

class SoilProfile(TypedDict, total=False):
    """Profile dict like SoilDataLoader.query_full_profile returns.

    total=False weil pro Adresse manche Quellen failen können
    (NL hat kein LUCAS, manche Punkte haben kein imperviousness etc.).
    Konsumenten müssen mit None/missing rechnen.
    """
    soilgrids: dict           # SoilGrids-Properties (soc/phh2o/clay/sand/silt/bdod/...)
    metals: dict              # LUCAS-Schwermetalle {cd: 0.5, pb: 23, ...}
    metal_status: dict        # {cd: {status: "warn", value: ..., ...}, ...}
    nutrients: dict           # LUCAS-Nährstoffe {n: 1.5, p: 22, k: 110, caco3: 3.2}
    corine: dict              # CORINE Land-Use-Lookup
    imperviousness_pct: float | None    # 0-100 (Copernicus HRL Imperviousness)
    awc_mm_m: float | None              # Available Water Capacity mm/m
    lucas_distance_km: float | None     # Distanz zum nächsten LUCAS-Probepunkt
    country_code: str         # "de" / "nl" / "at" / "ch"
    threshold_source: str     # z.B. "BBodSchV §8 Anhang 2"


# Frozen-Set aller erlaubten Top-Level-Keys. Konsumenten die andere Keys
# rauspulen → safe_pluck logged WARNING (Tippfehler-Detection).
SOIL_PROFILE_KEYS: frozenset[str] = frozenset({
    "soilgrids",
    "metals",
    "metal_status",
    "nutrients",
    "corine",
    "imperviousness_pct",
    "awc_mm_m",
    "lucas_distance_km",
    "country_code",
    "threshold_source",
})


def safe_pluck(profile: dict | None, key: str, default: Any = None) -> Any:
    """Get profile[key] mit Tippfehler-Warning.

    Verhält sich wie .get(), aber wenn `key` nicht in SOIL_PROFILE_KEYS
    deklariert ist → logger.warning. Damit fängt man Tippfehler wie
    'imperviousness' (richtig: 'imperviousness_pct') sofort beim
    nächsten Test-Lauf.

    Wenn profile None ist, return default ohne Warning (sparse Pipeline-
    Outputs sind erlaubt).
    """
    if profile is None:
        return default
    if key not in SOIL_PROFILE_KEYS:
        logger.warning(
            "soil_profile.%s is not a declared SoilProfile key — "
            "Tippfehler? Erlaubt: %s",
            key, sorted(SOIL_PROFILE_KEYS),
        )
    return profile.get(key, default)


# ──────────────────────────────────────────────────────────────────────────
# PillStatus — vom Backend gelieferte Status-Strings für Status-Pills
# ──────────────────────────────────────────────────────────────────────────

# Backend liefert engl. Strings (ok/warn/critical), CSS hat Aliase
# (full_report.css .pill.ok = .pill.stabil etc.). Diese Literal sind
# die Single source of truth für was die Templates erwarten.
PillStatus = Literal["ok", "warn", "critical", "muted"]

# Plus die deutschen CSS-Token-Namen, die die SVG-Visuals und Block-
# Separator-Pills nutzen (data-ampel="..."). Diese sind Designsystem-
# seitig, nicht Backend-seitig.
AmpelToken = Literal[
    "stabil", "leicht", "moderat", "auffaellig", "erheblich", "kritisch", "none",
]

# Mapping Backend-PillStatus → menschen-lesbares deutsches Label.
# Wird in section_08_schwermetalle.html benutzt; wenn mehr Sektionen
# Pills ohne Custom-Label brauchen, hier ergänzen statt jedes Template
# eigenes Mapping bauen.
PILL_STATUS_LABEL_DE: dict[str, str] = {
    "ok": "innerhalb Schwelle",
    "warn": "auffällig",
    "critical": "kritisch",
    "muted": "—",
}
