"""Admin activity endpoint — lightweight dashboard data from existing tables."""

import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models import Lead, Payment, Report, User

router = APIRouter(prefix="/api/_admin", tags=["admin"])

# Simple shared-secret admin token (set via env: ADMIN_TOKEN)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")


def _require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Reject requests without correct admin token. Skipped if ADMIN_TOKEN unset (dev mode)."""
    if not ADMIN_TOKEN:
        return  # Dev mode — no auth
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


@router.get("/stats")
async def stats(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
) -> dict:
    """High-level KPIs for the dashboard."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    leads_total = (await db.execute(select(func.count()).select_from(Lead))).scalar() or 0
    leads_today = (await db.execute(
        select(func.count()).select_from(Lead).where(Lead.created_at >= today_start)
    )).scalar() or 0
    leads_week = (await db.execute(
        select(func.count()).select_from(Lead).where(Lead.created_at >= week_start)
    )).scalar() or 0

    users_total = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    reports_total = (await db.execute(select(func.count()).select_from(Report))).scalar() or 0
    reports_paid = (await db.execute(
        select(func.count()).select_from(Report).where(Report.paid.is_(True))
    )).scalar() or 0

    # Breakdown: source (quiz vs landing_direct)
    source_rows = (await db.execute(
        select(Lead.source, func.count()).group_by(Lead.source)
    )).all()
    sources = {row[0]: row[1] for row in source_rows}

    return {
        "timestamp": now.isoformat(),
        "leads": {
            "total": leads_total,
            "today": leads_today,
            "week": leads_week,
            "by_source": sources,
        },
        "users": {"total": users_total},
        "reports": {
            "total": reports_total,
            "paid": reports_paid,
            "conversion_rate": round((reports_paid / reports_total * 100) if reports_total else 0, 1),
        },
    }


@router.get("/leads")
async def list_leads(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
) -> dict:
    """List recent leads with quiz answers."""
    result = await db.execute(
        select(Lead).order_by(Lead.created_at.desc()).limit(limit)
    )
    leads = result.scalars().all()
    return {
        "total": len(leads),
        "leads": [
            {
                "id": str(l.id),
                "email": l.email,
                "first_name": l.first_name,
                "last_name": l.last_name,
                "street": l.street,
                "house_number": l.house_number,
                "source": l.source,
                "quiz_answers": l.quiz_answers or {},
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in leads
        ],
    }


@router.get("/activity")
async def activity(db: AsyncSession = Depends(get_db)) -> dict:
    """Return user activity summary + recent actions derived from existing tables."""

    # ── Per-user summaries ──────────────────────────────────────────
    users_result = await db.execute(
        select(User).order_by(User.created_at.desc())
    )
    users = users_result.scalars().all()

    user_summaries = []
    for u in users:
        reports_result = await db.execute(
            select(func.count()).where(Report.user_id == u.id)
        )
        report_count = reports_result.scalar() or 0

        paid_result = await db.execute(
            select(func.count()).where(Report.user_id == u.id, Report.paid.is_(True))
        )
        paid_count = paid_result.scalar() or 0

        last_report = await db.execute(
            select(Report.created_at)
            .where(Report.user_id == u.id)
            .order_by(Report.created_at.desc())
            .limit(1)
        )
        last_report_at = last_report.scalar()

        actions: dict[str, int] = {"register": 1}
        if u.auth_provider != "email":
            actions["oauth_login"] = 1
        if report_count:
            actions["create_report"] = report_count
        if paid_count:
            actions["payment"] = paid_count

        user_summaries.append({
            "email": u.email,
            "total_actions": sum(actions.values()),
            "actions": actions,
            "first_seen": u.created_at.isoformat() if u.created_at else None,
            "last_seen": (last_report_at or u.created_at).isoformat() if (last_report_at or u.created_at) else None,
        })

    # ── Recent actions (last 50 reports + registrations) ────────────
    recent_reports = await db.execute(
        select(Report, User.email)
        .join(User, Report.user_id == User.id)
        .order_by(Report.created_at.desc())
        .limit(50)
    )

    recent: list[dict] = []
    for row in recent_reports:
        report, email = row.tuple()
        recent.append({
            "ts": report.created_at.isoformat() if report.created_at else None,
            "email": email,
            "action": "create_report",
            "endpoint": "POST /api/reports/create",
            "detail": f"{report.address_input} ({report.status})",
        })

    # Add user registrations as events
    for u in users:
        recent.append({
            "ts": u.created_at.isoformat() if u.created_at else None,
            "email": u.email,
            "action": "register" if u.auth_provider == "email" else "oauth_login",
            "endpoint": "POST /api/auth/register" if u.auth_provider == "email" else "POST /api/auth/social",
            "detail": f"Provider: {u.auth_provider}",
        })

    # Sort by timestamp descending
    recent.sort(key=lambda x: x["ts"] or "", reverse=True)
    recent = recent[:50]

    return {
        "total_entries": len(recent),
        "users": user_summaries,
        "recent": recent,
    }
