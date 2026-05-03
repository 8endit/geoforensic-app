"""Live smoke test for the LGB-RLP Bergbau WMS.

Use case: validate the AAK property-key whitelist
(``ampel``/``risiko``/``kategorie``/``klasse``/``color``/``farbe``) in
``app.mining_rlp._classify_one`` against a real coordinate that's known
to lie in an Altbergbau-Ampelkarte zone. Without this validation the
worst-of classifier may silently fall back to ``"vorhanden"`` because
none of the heuristic keys match the real WMS attribute names.

Usage::

    python -m scripts.mining_rlp_smoke_test \\
        --lat 49.249 --lon 7.014 \\
        --label "Saarbrücken Burbach (bekannte AAK-Zone)"

Or pass several test coordinates from a CSV with columns
``label,lat,lon``::

    python -m scripts.mining_rlp_smoke_test --csv test_coords.csv

The script does NOT use the database, the FastAPI app, or any Docker
container — it talks to the live LGB-RLP WMS endpoints directly. Run it
from the repo root (or anywhere with PYTHONPATH=backend).

Output: for each coordinate, dumps the raw ``berechtsame``- and
``altbergbau_raw``-features as JSON, plus the classifier's verdict.
Operator reads the property keys from the dumps and updates the
whitelist in ``backend/app/mining_rlp.py`` if needed.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from pathlib import Path

# Allow running from repo root without PYTHONPATH gymnastics.
HERE = Path(__file__).resolve()
BACKEND_ROOT = HERE.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.mining_rlp import (  # noqa: E402  (path-injection above is intentional)
    _classify_one,
    _extract_ampel_risk,
    query_mining_rlp,
)


def _format_features(features: list[dict], indent: int = 2) -> str:
    """Pretty-print WMS feature dicts so the operator can spot attribute keys fast."""
    return json.dumps(features, indent=indent, ensure_ascii=False, default=str)


def _print_unique_keys(features: list[dict], heading: str) -> None:
    """List which property keys actually showed up across all features.

    This is the key diagnostic — if the WMS returns a key like
    ``klassifizierung`` but our whitelist looks for ``klasse``, the
    classifier silently falls back to ``"vorhanden"``. Surfacing the
    unique key set lets the operator add the right name to the
    whitelist in app.mining_rlp.
    """
    keys: set[str] = set()
    for feat in features:
        keys.update(feat.keys())
    if not keys:
        print(f"  {heading}: (keine Attribute zurückgegeben)")
        return
    sorted_keys = sorted(keys)
    print(f"  {heading} unique attribute keys ({len(sorted_keys)}):")
    for k in sorted_keys:
        # Mark keys that are in our heuristic whitelist
        whitelisted = k.lower() in (
            "ampel", "risiko", "kategorie", "klasse", "color", "farbe",
        )
        marker = " ✓ matched by whitelist" if whitelisted else ""
        print(f"    - {k}{marker}")


async def _smoke_one(label: str, lat: float, lon: float) -> dict:
    print(f"\n=== {label} ===")
    print(f"  Coord: ({lat}, {lon})")
    try:
        result = await query_mining_rlp(lat, lon)
    except Exception as exc:  # noqa: BLE001
        print(f"  query_mining_rlp raised: {exc!r}")
        return {"label": label, "error": repr(exc)}

    print(f"  in_zone: {result['in_zone']}")
    print(f"  berechtsame hits: {len(result['berechtsame'])}")
    print(f"  altbergbau_raw features: {len(result['altbergbau_raw'])}")
    print(f"  altbergbau_risk (klassifiziert): {result['altbergbau_risk']!r}")

    _print_unique_keys(result["berechtsame"], "Berechtsame")
    _print_unique_keys(result["altbergbau_raw"], "AAK")

    # Per-feature classifier dry-run, so the operator sees which features
    # contributed which class to the worst-of result.
    if result["altbergbau_raw"]:
        print("  Per-feature classifier verdicts:")
        for i, feat in enumerate(result["altbergbau_raw"]):
            verdict = _classify_one(feat)
            print(f"    [{i}] {verdict!r}  (from {dict(feat)!r})")
        worst = _extract_ampel_risk(result["altbergbau_raw"])
        print(f"  Worst-of: {worst!r}  (this is what the report shows)")

    return result


async def _main_async(coords: list[tuple[str, float, float]]) -> None:
    for label, lat, lon in coords:
        await _smoke_one(label, lat, lon)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--lat", type=float, help="Latitude (single-coord mode)")
    parser.add_argument("--lon", type=float, help="Longitude (single-coord mode)")
    parser.add_argument(
        "--label", default="test", help="Label for the single-coord output",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="CSV with columns label,lat,lon — runs each row sequentially",
    )
    args = parser.parse_args()

    coords: list[tuple[str, float, float]] = []
    if args.csv:
        with args.csv.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                coords.append(
                    (row["label"], float(row["lat"]), float(row["lon"])),
                )
    elif args.lat is not None and args.lon is not None:
        coords.append((args.label, args.lat, args.lon))
    else:
        parser.error("Either --lat/--lon or --csv is required")

    if not coords:
        print("No coordinates to test.", file=sys.stderr)
        sys.exit(1)

    asyncio.run(_main_async(coords))


if __name__ == "__main__":
    main()
