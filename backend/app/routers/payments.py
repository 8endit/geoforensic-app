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
import os
import re
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
        # Production path: signed webhooks only.
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
    elif os.getenv("STRIPE_WEBHOOK_DEV_BYPASS") == "true":
        # Explicit opt-in: dev/test runner mit unsigned JSON. Niemals
        # ohne dieses Flag akzeptieren — sonst kann jeder POST an
        # /api/payments/webhook arbitrary `metadata.lead_id` schicken
        # und den Vollbericht-Trigger missbrauchen (free PDFs +
        # Brevo-Mail an beliebige Adressen, sieht legitim aus weil
        # source=stripe).
        try:
            event = json.loads(raw_payload.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body") from exc
        logger.warning("Stripe webhook accepting unsigned event (DEV_BYPASS=true)")
    else:
        # Mock-mode (no Stripe keys, no DEV_BYPASS): webhook is unused —
        # checkout endpoint triggers Vollbericht direkt via background
        # task. Webhook-Endpoint hier strict ablehnen damit der Pfad
        # nicht öffentlich exploitable ist.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook not configured (missing STRIPE_SECRET_KEY/STRIPE_WEBHOOK_SECRET)",
        )

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

        tier = _resolve_tier(metadata.get("tier"))

        # Re-trigger the lead pipeline with source="stripe" → PAID_SOURCES
        # → full report renderer + paid-mail template.
        from app.routers.leads import _generate_and_send_lead_report
        background_tasks.add_task(
            _generate_and_send_lead_report,
            email=email,
            address=address,
            answers={"source_metadata": "stripe-purchase",
                     "stripe_session_id": stripe_session_id,
                     "tier": tier},
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


# ── Bundle-Tier helpers ─────────────────────────────────────────────────

VALID_TIERS = {"basis", "komplett"}


def _resolve_tier(raw: str | None) -> str:
    """Normalize tier-input. Default 'basis'. Unknown → 'basis' (defensive)."""
    t = (raw or "basis").strip().lower()
    return t if t in VALID_TIERS else "basis"


def _resolve_country_pricing(country_code: str | None) -> str:
    """NL = launch-market (aggressiv); DE/AT/CH = standard. Andere → NL."""
    cc = (country_code or "").strip().lower()
    if cc in {"de", "at", "ch"}:
        return "de"
    return "nl"


# Heuristik: aus dem User-eingegebenen Adress-String den Land-Code raten.
# Spart einen extra Nominatim-Call beim Checkout (1s extra wäre vermeidbar).
# 99% korrekt fuer unsere Use-Cases, faellt fuer ambiguose Adressen
# (kein PLZ angegeben) auf NL = aggressiv = guenstiger zurueck → kunden-
# freundlicher Default als versehentlich DE-Pricing aufzwingen.
_NL_POSTCODE_IN_ADDRESS = re.compile(r"\b\d{4}\s?[A-Za-z]{2}\b")
_DE_POSTCODE_IN_ADDRESS = re.compile(r"\b\d{5}\b")
_AT_CH_POSTCODE_IN_ADDRESS = re.compile(r"\b\d{4}\b(?!\s?[A-Za-z]{2})")


def _country_from_address_input(address: str | None) -> str | None:
    """Best-effort Land-Detection aus User-Input. None wenn unklar.

    Reihenfolge wichtig: NL-PLZ matcht 4 Ziffern + 2 Buchstaben, das
    enthaelt auch eine Ziffernfolge die DE-PLZ-aehnlich aussieht. Erst
    NL pruefen.
    """
    if not address:
        return None
    s = address.strip()
    if _NL_POSTCODE_IN_ADDRESS.search(s):
        return "nl"
    if _DE_POSTCODE_IN_ADDRESS.search(s):
        return "de"
    if _AT_CH_POSTCODE_IN_ADDRESS.search(s):
        # AT vs CH lässt sich aus PLZ allein nicht trennen — beide haben
        # gleiches Pricing-Tier, also nehme "de" (= standard).
        return "de"
    # Wort-basierte Fallbacks: deutsche Großstadtnamen → "de"
    s_low = s.lower()
    if any(c in s_low for c in (
        "berlin", "münchen", "muenchen", "hamburg", "köln", "koeln",
        "frankfurt", "stuttgart", "düsseldorf", "duesseldorf",
        "leipzig", "dresden", "bremen", "hannover", "nürnberg", "nuernberg",
    )):
        return "de"
    if any(c in s_low for c in (
        "amsterdam", "rotterdam", "den haag", "utrecht", "eindhoven",
        "groningen", "tilburg", "maastricht", "haarlem",
    )):
        return "nl"
    return None


def _tier_price_cents(tier: str, country_code: str | None = None) -> int:
    """Preis fuer (tier, country). Default-Country ist NL (Launch-Markt).

    NL Basis 39 € / Komplett 59 €  vs.  DE/AT/CH 49 € / 89 €.
    EARLY50-Coupon wirkt prozentual auf beide (Stripe-Coupon ist 50 % off).
    """
    pricing = _resolve_country_pricing(country_code)
    if pricing == "de":
        if tier == "komplett":
            return settings.stripe_report_de_komplett_price_cents
        return settings.stripe_report_de_price_cents
    # NL / Default
    if tier == "komplett":
        return settings.stripe_report_komplett_price_cents
    return settings.stripe_report_price_cents


def _tier_product_label(tier: str) -> tuple[str, str]:
    """Return (name, description) für die Stripe-line_item product_data."""
    if tier == "komplett":
        return (
            "Bodenbericht — Vollbericht KOMPLETT",
            "12 Datensektionen + EU-Bodenrichtlinie + 5 Bonus-Module "
            "(Wind-Erosion separat, PAK/PCB, mikrobielle Aktivität, "
            "Bodenstruktur, Hydromorphologie). ~30 Seiten PDF.",
        )
    return (
        "Bodenbericht — Vollbericht BASIS",
        "12 Datensektionen + EU-Bodenrichtlinie 2025/2360 (alle 13 "
        "Descriptoren + 4 Versiegelungs-Indikatoren). ~30 Seiten PDF.",
    )


# ── Lead-flow checkout ──────────────────────────────────────────────────

class LeadCheckoutRequest(BaseModel):
    """Pre-filled by the Teaser-PDF CTA: lead_id from the lead record,
    email + address from what the user originally entered. We re-validate
    against the DB to make sure the (lead_id, email) pair is real.

    coupon_code is optional and only honored if it matches a known coupon
    (currently only "EARLY50") AND the lead is among the first N
    non-operator free leads.

    tier: "basis" (default, 12 Hauptsektionen) oder "komplett" (Basis + 5
    Bonus-Module). EARLY50 wirkt prozentual auf beide.
    """
    lead_id: uuid.UUID
    email: EmailStr
    address: str
    coupon_code: str | None = None
    tier: str = "basis"


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
        tier = _resolve_tier(payload.tier)
        logger.info("Stripe not configured — mock-mode Vollbericht (%s) for lead %s", tier, lead.id)
        from app.routers.leads import _generate_and_send_lead_report
        background_tasks.add_task(
            _generate_and_send_lead_report,
            email=payload.email,
            address=payload.address,
            answers={"source_metadata": "mock-purchase",
                     "mock_reason": "stripe_not_configured",
                     "tier": tier},
            db_url="",
            source="stripe",
            lead_id=lead.id,
        )
        return LeadCheckoutResponse(
            checkout_url=f"{settings.stripe_checkout_success_url}&mock=1&lead_id={lead.id}",
        )

    # 3. Live Stripe path
    stripe.api_key = settings.stripe_secret_key
    tier = _resolve_tier(payload.tier)
    tier_name, tier_desc = _tier_product_label(tier)
    # Country-Pricing: NL-Launch-Tarif vs DE/AT/CH-Standard.
    country = _country_from_address_input(payload.address)
    unit_amount = _tier_price_cents(tier, country)
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
                        "name": tier_name,
                        "description": f"Adresse: {payload.address[:200]} · {tier_desc}",
                    },
                    "unit_amount": unit_amount,
                },
                "quantity": 1,
            }
        ],
        "metadata": {
            "flow": "lead",
            "tier": tier,
            "country_pricing": country or "nl-default",
            "lead_id": str(lead.id),
            "email": payload.email,
            "address": payload.address[:480],
        },
        "automatic_tax": {"enabled": True},
    }

    # Apply EARLY50 coupon if requested + still within first-N quota.
    # Operator's own email is excluded from the count (so internal smoke
    # tests don't burn coupon slots).
    coupon_applied = False
    if payload.coupon_code and payload.coupon_code.upper() == "EARLY50":
        if await _early50_still_available(db, exclude_email=settings.operator_email):
            session_kwargs["discounts"] = [{"coupon": "EARLY50"}]
            coupon_applied = True
            logger.info("EARLY50 coupon applied for lead %s", lead.id)
            # Tax must be off when discounts is used in Checkout (Stripe
            # rejects automatic_tax + discounts combo in price_data mode).
            session_kwargs["automatic_tax"] = {"enabled": False}
        else:
            logger.info("EARLY50 coupon requested but quota exhausted for %s", lead.id)
    # Wenn KEIN Coupon programmatisch dran ist: Stripe-Promotion-Code-Feld
    # für User aktivieren — sie sehen ein Input-Feld auf der Stripe-Seite
    # und können den Code selbst eingeben (Domenico-Feedback 2026-05-05).
    # Promotion-Code muss im Stripe-Dashboard aus dem Coupon erstellt
    # worden sein (Coupon → "Kundenorientierte Codes verwenden").
    if not coupon_applied:
        session_kwargs["allow_promotion_codes"] = True

    try:
        session = stripe.checkout.Session.create(**session_kwargs)
    except stripe.error.StripeError as exc:
        logger.exception("Stripe session create failed for lead %s", lead.id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if not session.url:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Stripe returned no URL")

    logger.info("Stripe session %s created for lead %s", session.id, lead.id)
    return LeadCheckoutResponse(checkout_url=session.url)


# ── Direct-purchase from Landing-Page ──────────────────────────────────

class DirectCheckoutRequest(BaseModel):
    """Form input from the Landing-Page Direct-Purchase Modal: User gibt
    Adresse + Email ein, will sofort zur Bezahlung ohne den Mail-Detour
    über den kostenlosen Teaser.

    tier: "basis" oder "komplett" — Modell B Bundle-Tiers.
    """
    email: EmailStr
    address: str
    coupon_code: str | None = None
    tier: str = "basis"


@router.post("/checkout-direct", response_model=LeadCheckoutResponse)
async def create_checkout_direct(
    payload: DirectCheckoutRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> LeadCheckoutResponse:
    """Direct-purchase from Landing-Page: ein Schritt — kein Teaser-Detour.

    Legt Lead an (source="direct-purchase") und erzeugt sofort die
    Stripe-Session. Webhook macht später `_generate_and_send_lead_report
    (source="stripe")` für diesen Lead und mailt den Vollbericht.

    Coupon-Eligibility: der direkte Kauf ist normalerweise NICHT
    EARLY50-eligible (das ist der Lead-Magnet-Belohnungs-Mechanismus
    für die ersten 50 Teaser-Empfänger). Wenn `coupon_code=EARLY50`
    übergeben wird, prüfen wir denselben quota-Mechanismus wie beim
    Mail-Pfad — wer schnell genug ist, kriegt den Discount auch direkt.
    """
    if not payload.address or not payload.address.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Address required")

    # Lead-Row anlegen mit source="direct-purchase" für Analytics-Tracking.
    # (Source ist nicht in PAID_SOURCES — der Vollbericht wird vom
    # Webhook mit source="stripe" getriggert, nicht durch die Lead-Source.)
    lead = Lead(
        email=str(payload.email),
        source="direct-purchase",
        quiz_answers={"address_input": payload.address.strip()[:500]},
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    tier = _resolve_tier(payload.tier)

    # Mock-Mode (kein Stripe-Key): Vollbericht direkt triggern, redirect /danke.
    if not settings.stripe_secret_key:
        logger.info("Direct purchase mock-mode (%s) for new lead %s", tier, lead.id)
        from app.routers.leads import _generate_and_send_lead_report
        background_tasks.add_task(
            _generate_and_send_lead_report,
            email=str(payload.email),
            address=payload.address.strip(),
            answers={"source_metadata": "direct-purchase-mock", "tier": tier},
            db_url="",
            source="stripe",
            lead_id=lead.id,
        )
        return LeadCheckoutResponse(
            checkout_url=f"{settings.stripe_checkout_success_url}&mock=1&lead_id={lead.id}",
        )

    # Live-Stripe-Pfad
    stripe.api_key = settings.stripe_secret_key
    tier_name, tier_desc = _tier_product_label(tier)
    # Country-Pricing: NL Launch-Tarif vs DE/AT/CH Standard. Heuristik
    # aus PLZ in der User-Eingabe — kein extra Geocode-Call hier.
    country = _country_from_address_input(payload.address)
    unit_amount = _tier_price_cents(tier, country)
    session_kwargs = {
        "mode": "payment",
        "success_url": f"{settings.stripe_checkout_success_url}&session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": settings.stripe_checkout_cancel_url,
        "customer_email": str(payload.email),
        "line_items": [
            {
                "price_data": {
                    "currency": "eur",
                    "product_data": {
                        "name": tier_name,
                        "description": f"Adresse: {payload.address.strip()[:200]} · {tier_desc}",
                    },
                    "unit_amount": unit_amount,
                },
                "quantity": 1,
            }
        ],
        "metadata": {
            "flow": "lead",
            "tier": tier,
            "country_pricing": country or "nl-default",
            "lead_id": str(lead.id),
            "email": str(payload.email),
            "address": payload.address.strip()[:480],
        },
        "automatic_tax": {"enabled": True},
    }

    coupon_applied = False
    if payload.coupon_code and payload.coupon_code.upper() == "EARLY50":
        if await _early50_still_available(db, exclude_email=settings.operator_email):
            session_kwargs["discounts"] = [{"coupon": "EARLY50"}]
            session_kwargs["automatic_tax"] = {"enabled": False}
            coupon_applied = True
            logger.info("EARLY50 coupon applied for direct-purchase lead %s", lead.id)
    # Wenn KEIN Coupon programmatisch dran: User kann selbst eingeben.
    if not coupon_applied:
        session_kwargs["allow_promotion_codes"] = True

    try:
        session = stripe.checkout.Session.create(**session_kwargs)
    except stripe.error.StripeError as exc:
        logger.exception("Direct-purchase Stripe session create failed for lead %s", lead.id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if not session.url:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Stripe returned no URL")

    logger.info("Direct-purchase Stripe session %s created for lead %s", session.id, lead.id)
    return LeadCheckoutResponse(checkout_url=session.url)


# ── EARLY50 coupon helpers ──────────────────────────────────────────────

EARLY50_LIMIT = 50  # First N non-operator + non-test leads get the coupon


# Defensive Test-Pattern-Exklusion: alle Mails die wie ein interner Test
# aussehen, zaehlen NICHT in den 50er-Quota. Vorher (bis 2026-05-05) zaehlten
# alle non-operator-Mails — inkl. perfsmoke+/audit+/vbsmoke+/etc. — und
# verbrannten echte Kaeufer-Slots. Domains die wir bewusst behalten (echte
# externe Tester wie Domenico, Stefan, Gregor) zaehlen weiter normal.
_TEST_EMAIL_PATTERNS = (
    "%+audit%@%",         # +audit, +audit-de, +audit-nl, +audit-de2 etc.
    "%+perfsmoke%@%",     # scripts/perf_smoke.py
    "%+vbsmoke%@%",       # vollbericht-smoke
    "%+smoke%@%",         # generisch
    "%+test%@%",          # generisch
    "%+probe%@%",
    "%+banner@%",
    "%+livecheck%@%",
    "%+legacy@%",
    "%+log2@%",
    "%+t9@%",
    "earlytest%",         # earlytest@example.com
    "%@geoforensic.de",   # interne Test-Domain (gehoert uns)
)


def _early50_exclusion_clause():
    """SQLAlchemy-Where-Clause: alle Lead.email NOT LIKE pattern.

    Wird gemeinsam von _early50_still_available + is_early50_eligible
    benutzt damit die Quota-Logik konsistent bleibt.
    """
    from sqlalchemy import and_, not_, or_
    return and_(*[not_(Lead.email.like(p)) for p in _TEST_EMAIL_PATTERNS])


async def _early50_still_available(db: AsyncSession, exclude_email: str | None) -> bool:
    """True when fewer than EARLY50_LIMIT non-operator + non-test leads
    exist so far.
    """
    from sqlalchemy import func, select as _select
    stmt = _select(func.count(Lead.id)).where(_early50_exclusion_clause())
    if exclude_email:
        stmt = stmt.where(Lead.email != exclude_email)
    result = await db.execute(stmt)
    count = result.scalar_one() or 0
    return count <= EARLY50_LIMIT


async def is_early50_eligible(db: AsyncSession, lead: Lead, exclude_email: str | None) -> bool:
    """True for the lead if (a) it isn't the operator email, (b) it isn't
    a test-pattern email (audit/smoke/probe/etc, see _TEST_EMAIL_PATTERNS),
    and (c) the cumulative non-test-lead count at the time of *this* lead's
    insertion was within the EARLY50_LIMIT.

    Used by the teaser-PDF-renderer to decide whether to advertise the
    coupon code in the lead's mail.
    """
    if exclude_email and lead.email.lower() == exclude_email.lower():
        return False
    # Test-Pattern-Mails (audit+/smoke/probe/...) sind selber nicht eligible
    # — sonst wuerde ein Smoke-Test-Lead in seiner Mail noch eine EARLY50-
    # Anpreisung kriegen. Gleiches Pattern wie in _early50_still_available.
    e_low = lead.email.lower()
    test_patterns_lower = (
        "+audit", "+perfsmoke", "+vbsmoke", "+smoke", "+test",
        "+probe", "+banner", "+livecheck", "+legacy", "+log2", "+t9",
    )
    if e_low.startswith("earlytest") or e_low.endswith("@geoforensic.de"):
        return False
    if any(p in e_low for p in test_patterns_lower):
        return False
    from sqlalchemy import func, select as _select
    stmt = _select(func.count(Lead.id)).where(
        Lead.created_at <= lead.created_at,
        _early50_exclusion_clause(),
    )
    if exclude_email:
        stmt = stmt.where(Lead.email != exclude_email)
    result = await db.execute(stmt)
    rank = result.scalar_one() or 0
    return rank <= EARLY50_LIMIT

