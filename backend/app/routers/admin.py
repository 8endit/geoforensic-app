"""Admin activity endpoint — lightweight dashboard data from existing tables."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models import Payment, Report, User

router = APIRouter(prefix="/api/_admin", tags=["admin"])


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
