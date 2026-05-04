"""Stripe payment endpoints — checkout session + webhook + email delivery.

Two checkout flows:

1. **Legacy user-account flow** (`POST /checkout`): authenticated User has a
   completed Report in their dashboard, clicks "buy", we create a Stripe
   session bound to that report_id. Code path kept for backward compat but
   never triggered live (no user-facing dashboard exists today).

2. **Lead flow** (`POST /checkout-from-lead`): the actual public-facing path.
   The free Teaser PDF includes a "Vollbericht freischalten" CTA that links
   here with the recipient's lead_id, email, and the address that was
   originally screened. We create a Stripe session whose metadata carries
   those three values; on `checkout.session.completed` the webhook re-triggers
   the report pipeline with `source="stripe"` so the Vollbericht is generated
   for the same lead and mailed via Brevo.

Lead-flow auth: lead_id + email must match a row in the leads table. That
prevents random checkout sessions for arbitrary email addresses (cheap
spam-vector mitigation; Stripe itself blocks at the API level if abuse is
detected). Combined with the slowapi rate-limiter on `/api/leads/*` this
is enough for MVP.
"""

import asyncio
import json
import logging
import uuid

import stripe
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_current_user, get_db
from app.email_service import send_report_email
from app.models import Lead, Payment, PaymentStatus, Report, ReportStatus, User
from app.pdf_generator import generate_report_pdf
from app.schemas import CheckoutRequest, CheckoutResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["payments"])
settings = get_settings()


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    payload: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CheckoutResponse:
    result = await db.execute(select(Report).where(Report.id == payload.report_id, Report.user_id == current_user.id))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if report.status != ReportStatus.completed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Report is not completed yet")
    if report.paid:
        return CheckoutResponse(checkout_url=f"{settings.stripe_checkout_success_url}&report_id={report.id}")

    if settings.stripe_secret_key:
        stripe.api_key = settings.stripe_secret_key
        session = stripe.checkout.Session.create(
            mode="payment",
            success_url=f"{settings.stripe_checkout_success_url}&report_id={report.id}",
            cancel_url=f"{settings.stripe_checkout_cancel_url}&report_id={report.id}",
            line_items=[
                {
                    "price_data": {
                        "currency": "eur",
                        "product_data": {"name": f"GeoForensic Report {report.id}"},
                        "unit_amount": settings.stripe_report_price_cents,
                    },
                    "quantity": 1,
                }
            ],
            metadata={"report_id": str(report.id), "user_id": str(current_user.id)},
        )
        payment = Payment(
            report_id=report.id,
            stripe_session_id=session.id,
            status=PaymentStatus.pending,
            amount=settings.stripe_report_price_cents,
        )
        db.add(payment)
        await db.commit()
        return CheckoutResponse(checkout_url=session.url)

    stripe_session_id = f"cs_mock_{uuid.uuid4().hex}"
    checkout_url = f"{settings.stripe_checkout_success_url}&report_id={report.id}&session_id={stripe_session_id}"
    payment = Payment(
        report_id=report.id,
        stripe_session_id=stripe_session_id,
        status=PaymentStatus.completed,
        amount=settings.stripe_report_price_cents,
    )
    report.paid = True
    db.add(payment)
    await db.commit()

    # Send report email in mock mode (fire-and-forget)
    asyncio.create_task(_send_report_after_payment(report, current_user.email))

    return CheckoutResponse(checkout_url=checkout_url)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    raw_payload = await request.body()
    event: dict

    if settings.stripe_secret_key and settings.stripe_webhook_secret:
        stripe.api_key = settings.stripe_secret_key
        try:
            event_obj = stripe.Webhook.construct_event(
                payload=raw_payload,
                sig_header=stripe_signature or "",
                secret=settings.stripe_webhook_secret,
            )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid webhook: {exc}") from exc
        event = event_obj.to_dict()
    else:
        try:
            event = json.loads(raw_payload.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body") from exc

    if event.get("type") != "checkout.session.completed":
        return {"status": "ignored"}

    session_obj = event.get("data", {}).get("object", {})
    stripe_session_id = session_obj.get("id")
    if not stripe_session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing session id")

    # ── Lead-flow branch — metadata.flow == "lead" means the buyer came from
    # the Teaser-PDF CTA. Re-trigger the report pipeline with source="stripe"
    # so a Vollbericht is generated for the existing lead and mailed.
    metadata = session_obj.get("metadata") or {}
    if metadata.get("flow") == "lead":
        lead_id_raw = metadata.get("lead_id")
        email = metadata.get("email")
        address = metadata.get("address")
        if not (lead_id_raw and email and address):
            logger.warning("Stripe lead webhook missing metadata: %s", metadata)
            return {"status": "lead-metadata-incomplete"}

        try:
            lead_id = uuid.UUID(lead_id_raw)
        except ValueError:
            logger.warning("Stripe lead webhook invalid lead_id: %s", lead_id_raw)
            return {"status": "lead-id-invalid"}

        # Idempotency: if we already saw this session, no-op. Use the
        # existing payments table as ledger keyed on stripe_session_id.
        existing = await db.execute(
            select(Payment).where(Payment.stripe_session_id == stripe_session_id)
        )
        if existing.scalar_one_or_none() is not None:
            return {"status": "already-processed"}

        # Re-trigger the lead pipeline with source="stripe" → PAID_SOURCES
        # → full report renderer + paid-mail template.
        from app.routers.leads import _generate_and_send_lead_report
        background_tasks.add_task(
            _generate_and_send_lead_report,
            email=email,
            address=address,
            answers={"source_metadata": "stripe-purchase",
                     "stripe_session_id": stripe_session_id},
            db_url="",
            source="stripe",
            lead_id=lead_id,
        )
        logger.info("Stripe lead-flow triggered Vollbericht for lead %s", lead_id)
        return {"status": "ok-lead-flow"}

    # ── Legacy user-account branch — original Report+Payment row update.
    result = await db.execute(select(Payment).where(Payment.stripe_session_id == stripe_session_id))
    payment = result.scalar_one_or_none()
    if payment is None:
        return {"status": "unknown-session"}

    payment.status = PaymentStatus.completed
    report_result = await db.execute(select(Report).where(Report.id == payment.report_id))
    report = report_result.scalar_one_or_none()
    if report is not None:
        report.paid = True

        # Look up user email for notification
        user_result = await db.execute(select(User).where(User.id == report.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            asyncio.create_task(_send_report_after_payment(report, user.email))

    await db.commit()
    return {"status": "ok"}


async def _send_report_after_payment(report: Report, email: str) -> None:
    """Generate PDF and send it via email (fire-and-forget)."""
    try:
        pdf_bytes = generate_report_pdf(report)
        await send_report_email(
            recipient_email=email,
            report_address=report.address_input,
            pdf_bytes=pdf_bytes,
            report_id=str(report.id),
        )
    except Exception:
        logger.exception("Failed to send report email for %s to %s", report.id, email)


# ── Lead-flow checkout ──────────────────────────────────────────────────

class LeadCheckoutRequest(BaseModel):
    """Pre-filled by the Teaser-PDF CTA: lead_id from the lead record,
    email + address from what the user originally entered. We re-validate
    against the DB to make sure the (lead_id, email) pair is real.

    coupon_code is optional and only honored if it matches a known coupon
    (currently only "EARLY50") AND the lead is among the first N
    non-operator free leads.
    """
    lead_id: uuid.UUID
    email: EmailStr
    address: str
    coupon_code: str | None = None


class LeadCheckoutResponse(BaseModel):
    checkout_url: str


@router.post("/checkout-from-lead", response_model=LeadCheckoutResponse)
async def create_checkout_from_lead(
    payload: LeadCheckoutRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> LeadCheckoutResponse:
    """Public endpoint reached from the Teaser PDF CTA.

    Validates (lead_id, email) against the DB, then creates a Stripe Checkout
    Session whose `metadata` carries lead_id + email + address — the webhook
    uses those to re-trigger the report pipeline with `source="stripe"`.

    When Stripe is not configured (no STRIPE_SECRET_KEY in env, e.g. in dev
    or pre-onboarding), we run the mock-mode path: trigger the Vollbericht
    generation directly and return the success-URL, simulating a free
    paid-flow. This lets us test end-to-end before Stripe is live.

    When the EARLY50 coupon is in `payload.coupon_code` and is valid (lead
    is among the first EARLY50_LIMIT free leads, not the operator email),
    the Stripe session is created with the discount applied; mock-mode
    just notes the discount in logs.
    """
    # 1. Validate lead exists + email matches (case-insensitive)
    lead = await db.get(Lead, payload.lead_id)
    if lead is None or lead.email.lower() != payload.email.lower():
        # Same 404 either way so we don't leak which leg failed
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    # 2. Mock-mode: no Stripe configured → trigger Vollbericht directly,
    # redirect to /danke. This is the path you walk while Stripe is still
    # being onboarded — the buyer experience stays identical except no card
    # is charged.
    if not settings.stripe_secret_key:
        logger.info("Stripe not configured — mock-mode Vollbericht for lead %s", lead.id)
        from app.routers.leads import _generate_and_send_lead_report
        # FastAPI BackgroundTasks runs after the response is fully sent and
        # in the same event loop context — robuster als asyncio.create_task,
        # das mit der DB-Session-Lifecycle kollidiert.
        background_tasks.add_task(
            _generate_and_send_lead_report,
            email=payload.email,
            address=payload.address,
            answers={"source_metadata": "mock-purchase",
                     "mock_reason": "stripe_not_configured"},
            db_url="",
            source="stripe",
            lead_id=lead.id,
        )
        return LeadCheckoutResponse(
            checkout_url=f"{settings.stripe_checkout_success_url}&mock=1&lead_id={lead.id}",
        )

    # 3. Live Stripe path
    stripe.api_key = settings.stripe_secret_key
    session_kwargs = {
        "mode": "payment",
        "success_url": f"{settings.stripe_checkout_success_url}&session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": settings.stripe_checkout_cancel_url,
        "customer_email": payload.email,
        "line_items": [
            {
                "price_data": {
                    "currency": "eur",
                    "product_data": {
                        "name": "Bodenbericht — Vollbericht (Premium)",
                        "description": (
                            f"Adresse: {payload.address[:200]} · "
                            "12 Datensektionen, ~30 Seiten PDF, EU-Bodenrichtlinie konform."
                        ),
                    },
                    "unit_amount": settings.stripe_report_price_cents,
                },
                "quantity": 1,
            }
        ],
        "metadata": {
            # Stripe metadata: max 50 keys, max 500 chars per value
            "flow": "lead",
            "lead_id": str(lead.id),
            "email": payload.email,
            "address": payload.address[:480],
        },
        # Stripe Tax automatically computes DE 19% / NL 21% MwSt etc.
        # Requires Stripe Tax to be enabled in the dashboard.
        "automatic_tax": {"enabled": True},
    }

    # Apply EARLY50 coupon if requested + still within first-N quota.
    # Operator's own email is excluded from the count (so internal smoke
    # tests don't burn coupon slots).
    if payload.coupon_code and payload.coupon_code.upper() == "EARLY50":
        if await _early50_still_available(db, exclude_email=settings.operator_email):
            session_kwargs["discounts"] = [{"coupon": "EARLY50"}]
            logger.info("EARLY50 coupon applied for lead %s", lead.id)
            # Tax must be off when discounts is used in Checkout (Stripe
            # rejects automatic_tax + discounts combo in price_data mode).
            session_kwargs["automatic_tax"] = {"enabled": False}
        else:
            logger.info("EARLY50 coupon requested but quota exhausted for %s", lead.id)

    try:
        session = stripe.checkout.Session.create(**session_kwargs)
    except stripe.error.StripeError as exc:
        logger.exception("Stripe session create failed for lead %s", lead.id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if not session.url:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Stripe returned no URL")

    logger.info("Stripe session %s created for lead %s", session.id, lead.id)
    return LeadCheckoutResponse(checkout_url=session.url)


# ── EARLY50 coupon helpers ──────────────────────────────────────────────

EARLY50_LIMIT = 50  # First N non-operator free leads get the coupon


async def _early50_still_available(db: AsyncSession, exclude_email: str | None) -> bool:
    """True when fewer than EARLY50_LIMIT non-operator leads exist so far."""
    from sqlalchemy import func, select as _select
    stmt = _select(func.count(Lead.id))
    if exclude_email:
        stmt = stmt.where(Lead.email != exclude_email)
    result = await db.execute(stmt)
    count = result.scalar_one() or 0
    return count <= EARLY50_LIMIT


async def is_early50_eligible(db: AsyncSession, lead: Lead, exclude_email: str | None) -> bool:
    """True for the lead if (a) it isn't the operator email and (b) the
    cumulative non-operator-lead count at the time of *this* lead's
    insertion was within the EARLY50_LIMIT.

    Used by the teaser-PDF-renderer to decide whether to advertise the
    coupon code in the lead's mail.
    """
    if exclude_email and lead.email.lower() == exclude_email.lower():
        return False
    from sqlalchemy import func, select as _select
    stmt = _select(func.count(Lead.id)).where(Lead.created_at <= lead.created_at)
    if exclude_email:
        stmt = stmt.where(Lead.email != exclude_email)
    result = await db.execute(stmt)
    rank = result.scalar_one() or 0
    return rank <= EARLY50_LIMIT

