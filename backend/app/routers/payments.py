"""Stripe payment endpoints — checkout session + webhook + email delivery."""

import asyncio
import json
import logging
import uuid

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_current_user, get_db
from app.email_service import send_report_email
from app.models import Payment, PaymentStatus, Report, ReportStatus, User
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

