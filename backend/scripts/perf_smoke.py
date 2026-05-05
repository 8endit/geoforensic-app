"""Performance-Regression-Smoke-Test fuer die Vollbericht-Pipeline.

Wird nach jedem Deploy automatisch ausgefuehrt (siehe deploy/notes).
Ziel: verhindern dass eine Regression (z.B. ein gedroppter DB-Index, ein
neuer langsamer External-Call ohne Caching) unbemerkt durchrutscht und
Domenicos 3-Minuten-Vorfall zurueckkommt.

Schwellwerte sind so gesetzt dass sie typische Berlin-Adress-
Performance treffen:
    pipeline.egms_query  < 1 s   (mit Index ~50 ms typisch)
    pipeline.full_report < 10 s  (Chrome-Headless render)
    pipeline.TOTAL       < 25 s  (alles inkl. soil-loader, externe APIs,
                                  basemap-fetch, render, mail)

Bei Verletzung → exit 1 + Sentry-message + verbose log. Im docker-compose
deploy-pipeline ist das ein hard fail.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time

# Schwellwerte
EGMS_MAX_S = 1.0
FULL_REPORT_MAX_S = 10.0
TOTAL_MAX_S = 25.0

# Test-Adresse: Berlin Mitte hat ~78 PSI-Punkte → repraesentativer
# Mittelweg zwischen sparse (Land) und dense (NL Grossstadt).
TEST_ADDRESS = "Alexanderplatz 1, 10178 Berlin"
TEST_EMAIL = "perfsmoke@geoforensic.de"


async def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    log = logging.getLogger("perf_smoke")

    # Timings einsammeln aus den pipeline.* INFO-Logmeldungen.
    timings: dict[str, float] = {}

    class _TimingCapture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            msg = record.getMessage()
            if "pipeline." not in msg or "took=" not in msg:
                return
            # Format: "pipeline.<stage> took=<X.XX>s ..."
            try:
                stage_part, rest = msg.split(" took=", 1)
                stage = stage_part.split("pipeline.", 1)[1].strip()
                seconds = float(rest.split("s", 1)[0])
                timings[stage] = seconds
            except (ValueError, IndexError):
                pass

    handler = _TimingCapture()
    logging.getLogger("app.routers.leads").addHandler(handler)

    log.info("perf_smoke start — address=%s", TEST_ADDRESS)

    # Spaete Imports damit logging.basicConfig vor app-Imports steht.
    from app.routers.leads import _generate_and_send_lead_report
    from app.config import get_settings

    settings = get_settings()
    overall_t0 = time.perf_counter()
    try:
        await _generate_and_send_lead_report(
            email=TEST_EMAIL,
            address=TEST_ADDRESS,
            answers={"source_metadata": "perf_smoke", "tier": "komplett"},
            db_url=settings.database_url,
            source="stripe",
            lead_id=None,
        )
    except Exception:
        log.exception("perf_smoke FAILED — pipeline raised exception")
        return 1
    overall_s = time.perf_counter() - overall_t0
    log.info("perf_smoke pipeline done — wall_time=%.2fs", overall_s)
    log.info("captured timings: %s", timings)

    # Schwellwert-Pruefungen
    failures: list[str] = []

    egms = timings.get("egms_query")
    if egms is None:
        failures.append("pipeline.egms_query timing log not seen")
    elif egms > EGMS_MAX_S:
        failures.append(
            f"pipeline.egms_query={egms:.2f}s > {EGMS_MAX_S}s "
            f"(index moeglicherweise weg, vgl. alembic 20260505_01)"
        )

    fr = timings.get("full_report")
    if fr is None:
        failures.append("pipeline.full_report timing log not seen")
    elif fr > FULL_REPORT_MAX_S:
        failures.append(
            f"pipeline.full_report={fr:.2f}s > {FULL_REPORT_MAX_S}s "
            f"(Chrome-render Regression?)"
        )

    total = timings.get("TOTAL", overall_s)
    if total > TOTAL_MAX_S:
        failures.append(
            f"pipeline.TOTAL={total:.2f}s > {TOTAL_MAX_S}s "
            f"(externe Calls / soil-loader Regression?)"
        )

    if failures:
        log.error("perf_smoke FAILED:\n  %s", "\n  ".join(failures))
        # Sentry: wenn DSN gesetzt ist, alarmieren wir aktiv.
        if os.getenv("SENTRY_DSN"):
            try:
                import sentry_sdk
                sentry_sdk.init(
                    dsn=os.environ["SENTRY_DSN"],
                    environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
                    traces_sample_rate=0.0,
                )
                sentry_sdk.capture_message(
                    "perf_smoke regression: " + "; ".join(failures),
                    level="error",
                )
                sentry_sdk.flush(timeout=5)
            except Exception:  # noqa: BLE001
                pass
        return 1

    log.info(
        "perf_smoke OK — egms=%.2fs full_report=%.2fs total=%.2fs",
        egms or 0.0, fr or 0.0, total,
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
