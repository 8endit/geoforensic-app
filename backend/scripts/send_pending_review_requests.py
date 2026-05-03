"""Send Provenexpert review-request mails for reports older than N days.

Designed for cron. Picks up every Report whose lead has an email, that
was generated ≥ ``REVIEW_REQUEST_DELAY_DAYS`` ago, that hasn't already
been pinged (tracked via ``report_data.review_request_sent_at``), and
sends the friendly review-request mail via
``app.email_service.send_review_request_email``.

Idempotent — safe to run any time, even repeatedly:
- Tracks the per-report send timestamp inside the existing ``report_data``
  JSONB column. No alembic migration needed.
- Filters out reports that already have ``review_request_sent_at`` set.
- Filters out reports whose lead was created with no email or whose
  Lead row has been removed (``ON DELETE SET NULL`` keeps the report).

If ``PROVENEXPERT_REVIEW_URL`` is empty (Domenico hasn't created the
profile yet), the script logs that it's standing by and exits 0
without doing anything — still safe to schedule.

Usage::

    docker compose exec backend python -m scripts.send_pending_review_requests

Or as a one-shot ``docker compose run`` so it doesn't pin the backend
container:

    docker compose run --rm --entrypoint "" backend \\
        python -m scripts.send_pending_review_requests

For the cron config see ``docs/TEAM_HANDBOOK.md`` §4.4.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Path-injection so the script is repo-root-runnable without PYTHONPATH.
HERE = Path(__file__).resolve()
BACKEND_ROOT = HERE.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import selectinload  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.email_service import send_review_request_email  # noqa: E402
from app.models import Lead, Report  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
logger = logging.getLogger("review_requests")


async def _send_pending() -> tuple[int, int]:
    """Return (sent, skipped) counts."""
    settings = get_settings()
    review_url = (settings.provenexpert_review_url or "").strip()
    if not review_url:
        logger.info(
            "PROVENEXPERT_REVIEW_URL is empty — standing by, no mails sent. "
            "Set the variable in backend/.env once the Provenexpert profile exists."
        )
        return (0, 0)

    delay_days = max(1, int(settings.review_request_delay_days or 7))
    cutoff = datetime.now(timezone.utc) - timedelta(days=delay_days)
    logger.info(
        "Searching for reports created before %s (%d-day delay)",
        cutoff.isoformat(timespec="seconds"),
        delay_days,
    )

    sent = 0
    skipped = 0
    async with SessionLocal() as db:
        # We pull the Lead via the Report.lead relationship so we can use
        # the lead's email and skip rows where the lead was wiped.
        stmt = (
            select(Report)
            .options(selectinload(Report.lead))
            .where(Report.created_at <= cutoff)
            .where(Report.lead_id.is_not(None))
            .order_by(Report.created_at.asc())
        )
        result = await db.execute(stmt)
        reports = result.scalars().all()

        for report in reports:
            data = dict(report.report_data or {})
            if data.get("review_request_sent_at"):
                continue  # already pinged
            lead: Lead | None = report.lead
            if lead is None or not lead.email:
                skipped += 1
                continue

            address = report.address_input or "Ihre Adresse"
            ok = await send_review_request_email(
                recipient_email=lead.email,
                report_address=address,
                review_url=review_url,
            )
            if ok:
                data["review_request_sent_at"] = datetime.now(
                    timezone.utc,
                ).isoformat(timespec="seconds")
                report.report_data = data
                sent += 1
            else:
                skipped += 1

        if sent:
            await db.commit()
            logger.info("Committed %d updated report rows", sent)

    return (sent, skipped)


def main() -> None:
    sent, skipped = asyncio.run(_send_pending())
    logger.info("Done — sent=%d, skipped=%d", sent, skipped)


if __name__ == "__main__":
    main()
