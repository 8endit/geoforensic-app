"""Lead capture endpoint — quiz/landing form -> geocode -> report -> email.

Architecture:
    source in PAID_SOURCES     -> full PDF (geoforensic.de product)
    everything else (default)  -> short teaser PDF (bodenbericht.de lead magnet)

Routing is deny-by-default: a new landing form that emits an unfamiliar
source string falls through to the teaser, never to the full report.
Adding a new paid surface requires explicitly extending PAID_SOURCES
AFTER payment is confirmed by the upstream flow (Stripe webhook etc.).

Both paths share the same data pipeline (geocode, EGMS query, soil profile)
and persist a Report row. They differ only in the PDF rendering step and
the wording of the outbound mail (see ``email_service.is_teaser``).
"""

import asyncio
import logging
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_db
from app.email_service import send_report_email, send_waitlist_confirmation_email
from app.flood_data import query_flood
from app.full_report import generate_full_report
from app.html_report import generate_html_report
from app.kostra_data import KostraLoader
from app.mining_de import query_mining
from app.models import Ampel, Lead, Report, ReportStatus
from app.pdf_renderer import html_to_pdf
from app.rate_limit import limiter
from app.routers.reports import geocode_address
from app.soil_data import SoilDataLoader
from app.static_map import fetch_static_map

router = APIRouter(prefix="/api/leads", tags=["leads"])
logger = logging.getLogger(__name__)

# Lead-Flow-Routing — deny-by-default.
#
# The full PDF is the paid product (geoforensic.de). The teaser PDF is the
# free lead magnet (bodenbericht.de). To make sure no free lead ever
# accidentally triggers the full report — e.g. because a new form on the
# landing page sets a source string we forgot to whitelist — the routing
# is deny-by-default: only sources explicitly listed in PAID_SOURCES get
# the full report. Everything else falls through to the teaser.
#
# When the paid flow is wired up (Stripe checkout etc.), it will set
# source="paid" (or another value listed here) AFTER payment confirmation.
#
# Discount-Strategie für Early-Bird ist EARLY50-Coupon im Stripe-Path
# (siehe `is_early50_eligible` in routers/payments.py): erste 50
# non-operator Leads bekommen 50 % Rabatt aufs Vollbericht-Pricing.
# Vorher gab's eine separate `pilot-vollbericht` Source die kostenlos
# Vollbericht emittierte (Pilot-Section auf Landing) — entfernt
# 2026-05-05: redundant + irreführend ("kostenlos für 50" widersprach
# der eigentlichen Discount-Strategie + Teaser ist eh schon kostenlos
# als Lead-Magnet).
PAID_SOURCES = {"paid", "checkout", "stripe"}

# Marketing-style sources that require double-opt-in per UWG § 7 Abs. 2 Nr. 2.
# A lead with one of these sources is created with a confirmation token and
# receives a confirmation mail; the row stays "pending" until the user clicks
# the link, which sets confirmed_at via /api/leads/confirm/{token}.
DOI_SOURCES = {"premium-waitlist"}


class LeadCreate(BaseModel):
    email: EmailStr
    address: str | None = None
    answers: dict | None = None
    timestamp: str | None = None
    source: str = "quiz"
    # Honeypot: legitimate users never see this field; bots fill every input
    # they find. Any non-empty value flips this lead into the silently-discarded
    # bot bucket. Field name "website" is generic enough to attract naive
    # scraper bots without raising suspicion in their fill heuristics.
    website: str | None = None


class LeadResponse(BaseModel):
    id: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


def _ampel_from_velocity(mean_abs_velocity: float) -> str:
    """Classify the Ampel based on mean absolute velocity (mm/year).

    Threshold rationale: 2 mm/a is the standard yellow boundary used
    throughout the app. 5 mm/a is the red threshold above which we
    explicitly recommend a Gutachter. These thresholds drive the
    Ampel only — the continuous score is computed separately by
    ``_compute_geo_score`` below.
    """
    if mean_abs_velocity < 2:
        return "gruen"
    if mean_abs_velocity <= 5:
        return "gelb"
    return "rot"


def _compute_geo_score(
    velocities: list[float],
    timeseries: list,
) -> int | None:
    """Continuous 0-100 GeoScore from a list of absolute velocities (mm/a)
    plus the optional quarterly displacement time-series.

    Components, each subtracted from a base of 100:
      mean velocity          ×12   main subsidence/uplift signal
      max velocity            ×4   hot-spot at any single point
      std deviation           ×6   heterogeneity of the area
      density floor                sparse data caps the score
      trend penalty           -5   time series accelerating

    Returns ``None`` when there are no measurements — the Teaser
    template renders that as "k. A." rather than a misleading number.

    The PDF copy that explains the score MUST stay aligned with what
    this function actually does. If the formula changes, update the
    explanatory text in ``html_report.py`` and ``full_report.py``.
    """
    n = len(velocities)
    if n == 0:
        return None

    mean_v = sum(velocities) / n
    max_v = max(velocities)

    if n > 1:
        variance = sum((v - mean_v) ** 2 for v in velocities) / n
        std_v = variance ** 0.5
    else:
        std_v = 0.0

    score = 100.0
    score -= mean_v * 12
    score -= max_v * 4
    score -= std_v * 6

    # Density floor — sparse data is statistically less reliable, so we
    # don't claim a top score even if the few points we have look fine.
    if n < 10:
        score = min(score, 60)
    elif n < 25:
        score = min(score, 78)

    # Trend penalty — if the cumulative-displacement time series shows
    # the second half drifting further from zero than the first half by
    # more than 0.5 mm, the location is in an active phase. Deduct 5.
    if timeseries and len(timeseries) >= 4:
        n_ts = len(timeseries)
        first = timeseries[: n_ts // 2]
        second = timeseries[n_ts // 2 :]
        if first and second:
            first_mean = sum(v for _, v in first) / len(first)
            second_mean = sum(v for _, v in second) / len(second)
            if abs(second_mean) > abs(first_mean) + 0.5:
                score -= 5

    return int(round(max(0, min(100, score))))


async def _generate_and_send_lead_report(
    email: str,
    address: str,
    answers: dict,
    db_url: str,
    geocoded: tuple[float, float, str, str, dict] | None = None,
    source: str = "quiz",
    lead_id: "uuid.UUID | None" = None,
) -> None:
    """Background task: geocode → EGMS query → PDF → email.

    Accepts pre-computed geocode (lat, lon, display_name, country_code) from the
    synchronous validation in the request handler; falls back to geocoding here
    for backward compatibility.

    The ``source`` argument selects which report variant gets rendered and
    which email template is used.  Sources in ``PAID_SOURCES`` yield the
    full PDF (`generate_full_report`); everything else falls through to the
    teaser. Both share the geocode + EGMS + soil pipeline below.
    """
    from app.database import SessionLocal

    is_teaser = source not in PAID_SOURCES

    try:
        # 1. Geocode (or use pre-computed result from request handler)
        if geocoded is not None:
            lat, lon, display_name, country_code, region = geocoded
        else:
            lat, lon, display_name, country_code, region = await geocode_address(address)

        # 2. EGMS query — radius comes from settings so copy in the PDF
        #    and the SQL query can never drift apart.
        settings = get_settings()
        radius_m = settings.egms_radius_m
        # Threshold above which a measurement point counts as "elevated" for
        # the Ampel-begruendung line in the report. 2 mm/a is the
        # standard gelb/yellow boundary used throughout the app.
        ELEVATED_THRESHOLD_MM_YR = 2.0
        async with SessionLocal() as db:
            result = await db.execute(
                text(
                    """
                    SELECT
                        mean_velocity_mm_yr,
                        ST_Distance(
                            geom::geography,
                            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                        ) AS distance_m
                    FROM egms_points
                    WHERE ST_DWithin(
                        geom::geography,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                        :radius_m
                    )
                    ORDER BY distance_m ASC
                    """
                ),
                {"lat": lat, "lon": lon, "radius_m": radius_m},
            )
            points = [dict(row._mapping) for row in result]

            # Aggregated quarterly time series across all points in the radius.
            # Values are average cumulative displacement in mm — we hand them
            # to the report template which renders a qualitative chart (no
            # numeric y-axis labels), so the raw mm numbers stay behind the
            # paywall while the shape of the trend is visible for free.
            ts_result = await db.execute(
                text(
                    """
                    SELECT
                        DATE_TRUNC('quarter', t.measurement_date)::date AS period,
                        AVG(t.displacement_mm) AS avg_displacement
                    FROM egms_timeseries t
                    JOIN egms_points p ON t.point_id = p.id
                    WHERE ST_DWithin(
                        p.geom::geography,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                        :radius_m
                    )
                    GROUP BY period
                    ORDER BY period
                    """
                ),
                {"lat": lat, "lon": lon, "radius_m": radius_m},
            )
            timeseries = [
                (row._mapping["period"], float(row._mapping["avg_displacement"]))
                for row in ts_result
            ]

        # 3. Compute metrics — DISTANZ-GEWICHTETER Mittelwert.
        #
        # Punkte direkt an der Adresse dominieren die Ampel; entfernte
        # Punkte ziehen den Mittelwert nicht ungebührlich in eine Richtung.
        # Verhindert False-Positives (Nachbarquartier 400 m weg hat
        # Senkung → falsch-gelbes Haus) und False-Negatives (eigener
        # Block senkt sich, Umgebung stabil → falsch-grünes Haus).
        #
        # Schema: w_i = 1 / max(d_i, 50 m). Inverse Distanz, linear (1/d)
        # statt 1/d², damit nicht 5 sehr-nahe Punkte 65 weiter entfernte
        # komplett überstimmen. 50 m-Floor entspricht typischer PSI-Spacing
        # in dichter Stadt und verhindert Division durch Werte < 1 m.
        # Identisches Schema in routers/reports.py (V.1 hatte dort linear
        # taper 1.0 → 0.1, jetzt synchronisiert).
        DIST_FLOOR_M = 50.0
        if points:
            velocities = [abs(float(p["mean_velocity_mm_yr"])) for p in points]
            weights = [1.0 / max(float(p["distance_m"]), DIST_FLOOR_M) for p in points]
            weight_sum = sum(weights)
            mean_v = sum(v * w for v, w in zip(velocities, weights)) / weight_sum
            max_v = max(velocities)
            ampel = _ampel_from_velocity(mean_v)
            geo_score = _compute_geo_score(velocities, timeseries)
            elevated_count = sum(1 for v in velocities if v > ELEVATED_THRESHOLD_MM_YR)
        else:
            mean_v, max_v, ampel, geo_score = 0.0, 0.0, "gruen", None
            elevated_count = 0

        # 4. Query soil data (SoilGrids + LUCAS + CORINE) — country-routed so
        #    NL addresses do not get DE-LUCAS values interpolated from 200km away
        #    and DE-thresholds (BBodSchV) do not appear on a Dutch report.
        try:
            soil_loader = SoilDataLoader.get()
            soil_profile = soil_loader.query_full_profile(lat, lon, country_code=country_code)
        except Exception:
            logger.warning("Soil data query failed for (%s, %s), using empty profile", lat, lon)
            soil_profile = {}

        # 4b. EU Soil Monitoring Directive (16 descriptors) — only for the full
        #     report, never for the teaser. Runs synchronously here because we
        #     need it before generate_full_report; query is < 50 ms (all local
        #     raster reads + KD-tree LUCAS lookup).
        soil_directive_data: dict | None = None

        # 5. Generate the PDF. Teaser variant uses the HTML template +
        #    Chrome-headless renderer (with a static OSM map on page 1);
        #    the full variant uses FPDF directly and does not embed a
        #    map, so we skip the static-map fetch in that branch.
        # mining_data, kostra_data, flood_data carry the per-layer
        # lookup results (or None if not queried for this address /
        # branch). Defined here so they stay in scope for the audit log
        # in step 6 regardless of which branch ran.
        mining_data: dict | None = None
        kostra_data: dict | None = None
        flood_data: dict | None = None
        if is_teaser:
            map_data_uri = await fetch_static_map(lat, lon)
            # EARLY50-Check vorab: nur Teaser-Empfänger, deren Lead unter
            # den ersten 50 nicht-Operator-Leads ist, sehen den Coupon.
            _early50_eligible = False
            if lead_id is not None:
                from app.routers.payments import is_early50_eligible
                _the_lead = await db.get(Lead, lead_id)
                if _the_lead is not None:
                    _early50_eligible = await is_early50_eligible(
                        db, _the_lead, exclude_email=settings.operator_email,
                    )
            html = generate_html_report(
                address=display_name,
                lat=lat,
                lon=lon,
                ampel=ampel,
                point_count=len(points),
                mean_velocity=mean_v,
                max_velocity=max_v,
                geo_score=geo_score,
                soil_profile=soil_profile,
                answers=answers or {},
                radius_m=radius_m,
                map_data_uri=map_data_uri,
                region=region,
                timeseries=timeseries,
                elevated_count=elevated_count,
                elevated_threshold_mm_yr=ELEVATED_THRESHOLD_MM_YR,
                # Stripe-CTA: lead_id + email aktivieren den /kaufen-Link
                # statt des Warteliste-Fallbacks. Wirken nur wenn Stripe
                # serverseitig konfiguriert ist (sonst no-op-Mock-Pfad).
                lead_id=str(lead_id) if lead_id else None,
                recipient_email=email,
                # EARLY50 coupon: Lead bekommt einen sichtbaren Rabatt-Code
                # in der CTA, wenn er zu den ersten 50 Test-Empfaengern
                # gehoert (Operator-Email ausgeschlossen).
                coupon_code=("EARLY50" if _early50_eligible else None),
                coupon_label=("50 %" if _early50_eligible else None),
            )
            pdf_bytes = html_to_pdf(html)
            if pdf_bytes is None:
                # Fallback: send HTML as attachment
                pdf_bytes = html.encode("utf-8")
                logger.warning("PDF rendering failed, sending HTML as fallback for %s", email)
        else:
            # Bergbau: dispatcher routes per Bundesland.
            # NRW -> Bezirksregierung Arnsberg WMS (Berechtsame).
            # RLP / Saarland -> LGB-RLP WMS (Berechtsame + Altbergbau-Ampelkarte;
            # das Oberbergamt Saarbrücken ist für beide Länder zuständig).
            # Andere Bundesländer -> kein WMS verfügbar, Section rendert
            # den Behörden-Auskunft-Placeholder.
            state = (region or {}).get("state")
            try:
                mining_data = await query_mining(lat, lon, state)
            except Exception:
                logger.exception(
                    "Bergbau dispatcher failed for (%s, %s, %s); "
                    "report will render the service-unavailable notice.",
                    lat, lon, state,
                )
                mining_data = None

            # BfG Hochwasser: nationaler Aggregat, deckt DE-Adressen ab.
            # Bei NL/AT/CH liefert das WMS einfach nichts und die Sektion
            # zeigt "nicht im Gebiet" — das ist akzeptabel als first cut;
            # eine Country-Gate-Optimierung können wir später ergänzen.
            if country_code.lower() == "de":
                try:
                    flood_data = await query_flood(lat, lon)
                except Exception:
                    logger.exception(
                        "BfG flood lookup failed unexpectedly for (%s, %s); "
                        "report will render the service-unavailable notice.",
                        lat, lon,
                    )
                    flood_data = {
                        "any_in_zone": False,
                        "scenarios": {},
                        "error": "lookup_exception",
                    }

            # KOSTRA Starkregen: für alle DE-Adressen, sofern Raster
            # verfügbar. Loader-Singleton degradiert sauber wenn die
            # Files nicht auf Platte liegen — query() liefert dann
            # available=False und der Report rendert "Daten in
            # Vorbereitung".
            if country_code.lower() == "de":
                try:
                    kostra_data = KostraLoader.get().query(lat, lon)
                except Exception:
                    logger.exception(
                        "KOSTRA lookup failed unexpectedly for (%s, %s); "
                        "report will render the unavailable-state notice.",
                        lat, lon,
                    )
                    kostra_data = {"available": False, "slots": {}}

            # 4b. Slope analysis — multi-scale Open-Elevation lookup. Result
            # feeds RUSLE LS-factor (otherwise default 2° flattens hillside
            # erosion estimates) AND becomes its own "Geländeprofil" section.
            slope_data: dict | None = None
            slope_deg_for_directive: float | None = None
            try:
                from app.slope_data import fetch_slope
                slope_data = await fetch_slope(lat, lon, country_code=country_code)
                if slope_data and slope_data.get("available"):
                    slope_deg_for_directive = slope_data.get("slope_deg")
            except Exception:
                logger.exception(
                    "Slope analysis failed for (%s, %s); RUSLE will use 2° default",
                    lat, lon,
                )
                slope_data = None

            # 4c. EU Soil Directive descriptors with the real slope value.
            try:
                from app.soil_directive import query_soil_directive
                soil_directive_data = await asyncio.to_thread(
                    query_soil_directive,
                    lat, lon, slope_deg_for_directive, country_code,
                )
            except Exception:
                logger.exception(
                    "Soil-directive query failed for (%s, %s); section will be skipped",
                    lat, lon,
                )
                soil_directive_data = None

            # 4d. Altlasten — country-routed. NL hits PDOK Bodemloket WMS
            # (real cataster); DE returns a CORINE land-use proxy plus a
            # pointer to authority enquiry. Both fail gracefully.
            altlasten_data: dict | None = None
            try:
                from app.altlasten_data import fetch_altlasten
                altlasten_data = await fetch_altlasten(lat, lon, country_code=country_code)
            except Exception:
                logger.exception(
                    "Altlasten lookup failed for (%s, %s); section will be skipped",
                    lat, lon,
                )
                altlasten_data = None

            # FPDF is synchronous and CPU-bound — wrap in to_thread so a
            # multi-second render does not block the event loop and starve
            # other inbound /api/leads requests.
            pdf_bytes = await asyncio.to_thread(
                generate_full_report,
                address=display_name,
                lat=lat,
                lon=lon,
                ampel=ampel,
                point_count=len(points),
                mean_velocity=mean_v,
                max_velocity=max_v,
                geo_score=geo_score,
                soil_profile=soil_profile,
                answers=answers or {},
                mining_data=mining_data,
                kostra_data=kostra_data,
                flood_data=flood_data,
                soil_directive_data=soil_directive_data,
                altlasten_data=altlasten_data,
                slope_data=slope_data,
                country_code=country_code,
            )

        # 6. Persist a Report row for this lead (C1). The row carries all
        #    structured values the template used — ampel, geo_score,
        #    point_count, elevated_count, mean/max velocity, region, how
        #    many timeseries quarters were available — so the admin can
        #    audit what went into the mail without re-running the pipeline.
        #
        #    The PDF bytes themselves are NOT stored here (see ticket C2).
        #    Exception safety: any DB failure is logged and swallowed so
        #    the email still goes out. Losing the email over a DB hiccup
        #    would be worse than losing the audit spur for that one lead.
        report_id: uuid.UUID | None = None
        if lead_id is not None:
            try:
                country_code_str = (country_code or "").upper()[:2] or "DE"
                report_data = {
                    "point_count": len(points),
                    "elevated_count": elevated_count,
                    "elevated_threshold_mm_yr": ELEVATED_THRESHOLD_MM_YR,
                    "mean_velocity_mm_yr": round(mean_v, 3) if points else None,
                    "max_velocity_mm_yr": round(max_v, 3) if points else None,
                    "timeseries_quarters": len(timeseries),
                    "radius_m": radius_m,
                    "region": region or {},
                    "source": source,
                    "is_teaser": is_teaser,
                    "address_display": display_name,
                    # Compact audit records of the per-layer lookups —
                    # full feature attributes stay out of the audit JSONB.
                    "mining": (
                        {
                            "provider": mining_data.get("provider"),
                            "available": bool(mining_data.get("available")),
                            "in_zone": bool(mining_data.get("in_zone")),
                            "hits_count": len(mining_data.get("hits") or []),
                            "altbergbau_risk": mining_data.get("altbergbau_risk"),
                            "error": mining_data.get("error"),
                        }
                        if mining_data is not None
                        else None
                    ),
                    "flood_bfg": (
                        {
                            "any_in_zone": bool(flood_data.get("any_in_zone")),
                            "scenarios_in_zone": [
                                k for k, v in (flood_data.get("scenarios") or {}).items()
                                if v.get("in_zone") is True
                            ],
                            "error": flood_data.get("error"),
                        }
                        if flood_data is not None
                        else None
                    ),
                    "kostra": (
                        {
                            "available": bool(kostra_data.get("available")),
                            "slots_with_value": [
                                k for k, v in (kostra_data.get("slots") or {}).items()
                                if v.get("value") is not None
                            ],
                        }
                        if kostra_data is not None
                        else None
                    ),
                }
                async with SessionLocal() as db:
                    ampel_enum = Ampel(ampel) if ampel in {"gruen", "gelb", "rot"} else None
                    report = Report(
                        user_id=None,
                        lead_id=lead_id,
                        address_input=display_name,
                        latitude=lat,
                        longitude=lon,
                        radius_m=radius_m,
                        country=country_code_str,
                        status=ReportStatus.completed,
                        ampel=ampel_enum,
                        geo_score=geo_score,
                        paid=False,
                        report_data=report_data,
                        # Persist the exact PDF bytes that were just mailed
                        # so the admin can redownload the historic version.
                        # On HTML fallback (PDF-render failed, pdf_bytes
                        # already contains html.encode('utf-8')), we still
                        # store it — the endpoint's Content-Type check
                        # handles that case.
                        pdf_bytes=pdf_bytes,
                    )
                    db.add(report)
                    await db.commit()
                    await db.refresh(report)
                    report_id = report.id
            except Exception:
                logger.exception(
                    "Failed to persist Report row for lead_id=%s (email=%s) — "
                    "mail will still be sent, audit spur is lost for this lead.",
                    lead_id, email,
                )

        # 7. Send email
        await send_report_email(
            recipient_email=email,
            report_address=display_name,
            pdf_bytes=pdf_bytes,
            report_id=f"lead-{email}",
            is_teaser=is_teaser,
        )
        logger.info(
            "Lead report sent to %s for address %s (%s, %d pts, source=%s, teaser=%s, report_id=%s)",
            email, address, ampel, len(points), source, is_teaser, report_id,
        )

    except Exception:
        logger.exception("Failed to generate lead report for %s", email)


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/hour")
async def capture_lead(
    request: Request,
    payload: LeadCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Honeypot: bots fill every input including the hidden one.  Return a
    # 201 so the client doesn't learn the trap exists, but skip everything
    # downstream (no DB write, no mail, no geocode).
    if payload.website and payload.website.strip():
        logger.info(
            "Honeypot triggered (source=%s, ip=%s) — silently discarded",
            payload.source,
            getattr(request.client, "host", "?"),
        )
        # Return a fake LeadResponse so the bot client sees success.
        return LeadResponse(
            id=str(uuid.uuid4()),
            email=payload.email,
            created_at=datetime.now(timezone.utc),
        )

    # DOI sources (premium-waitlist) bypass the geocode + report path: we
    # only collect the email behind a token-gated confirmation, no PDF.
    if payload.source in DOI_SOURCES:
        token = secrets.token_urlsafe(32)
        lead = Lead(
            email=payload.email,
            quiz_answers=dict(payload.answers or {}),
            source=payload.source,
            confirmation_token=token,
        )
        db.add(lead)
        await db.commit()
        await db.refresh(lead)

        # Premium-Waitlist is bodenbericht.de-exclusive — confirmation link
        # must NEVER point at geoforensic.de (which is currently parked).
        confirm_url = f"https://bodenbericht.de/api/leads/confirm/{token}"
        background_tasks.add_task(
            send_waitlist_confirmation_email,
            recipient_email=payload.email,
            confirm_url=confirm_url,
        )
        return LeadResponse(
            id=str(lead.id), email=lead.email, created_at=lead.created_at
        )

    # If address provided: validate synchronously via geocoding BEFORE saving
    # the lead, so the user gets immediate feedback on typos instead of a silent
    # failure in the background report pipeline.
    geocoded: tuple[float, float, str, str, dict] | None = None
    address_clean: str | None = None
    if payload.address and payload.address.strip():
        address_clean = payload.address.strip()
        # geocode_address raises HTTPException(422) if Nominatim returns no
        # results; that propagates as-is to the client with detail message
        # "Adresse konnte nicht gefunden werden".
        geocoded = await geocode_address(address_clean)

    # Merge address into quiz_answers so it's visible in admin dashboard
    answers_with_address = dict(payload.answers or {})
    if payload.address:
        answers_with_address["address"] = payload.address

    lead = Lead(
        email=payload.email,
        quiz_answers=answers_with_address,
        source=payload.source,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    # Schedule background report generation with the already-verified
    # geocode. lead.id is forwarded so the background task can link its
    # Report row back to this Lead for audit.
    if address_clean and geocoded:
        background_tasks.add_task(
            _generate_and_send_lead_report,
            email=payload.email,
            address=address_clean,
            answers=payload.answers or {},
            db_url="",  # uses SessionLocal directly
            geocoded=geocoded,
            source=payload.source,
            lead_id=lead.id,
        )

    return LeadResponse(
        id=str(lead.id),
        email=lead.email,
        created_at=lead.created_at,
    )


_DOI_CONFIRMED_HTML = """<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Anmeldung bestätigt - Bodenbericht</title>
<link rel="stylesheet" href="/tailwind.css"></head>
<body class="font-sans bg-gray-50 min-h-screen flex items-center justify-center p-6">
  <div class="max-w-md w-full bg-white rounded-2xl shadow-sm border border-gray-200 p-8 text-center">
    <div class="w-14 h-14 rounded-full bg-brand-500/15 flex items-center justify-center mx-auto mb-4">
      <svg class="w-8 h-8 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
    </div>
    <h1 class="text-2xl font-bold text-navy-900 mb-2">Anmeldung bestätigt</h1>
    <p class="text-gray-600 leading-relaxed mb-6">Sie sind auf der Premium-Bericht-Warteliste eingetragen. Wir melden uns, sobald der Bericht verfügbar ist.</p>
    <a href="/" class="inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white font-semibold px-5 py-2.5 rounded-lg transition">Zur Startseite</a>
  </div>
</body></html>"""

_DOI_INVALID_HTML = """<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bestätigungslink ungültig - Bodenbericht</title>
<link rel="stylesheet" href="/tailwind.css"></head>
<body class="font-sans bg-gray-50 min-h-screen flex items-center justify-center p-6">
  <div class="max-w-md w-full bg-white rounded-2xl shadow-sm border border-gray-200 p-8 text-center">
    <h1 class="text-2xl font-bold text-navy-900 mb-2">Bestätigungslink ungültig</h1>
    <p class="text-gray-600 leading-relaxed mb-6">Der Link ist abgelaufen, falsch kopiert oder bereits verwendet. Sie können sich erneut für die Warteliste eintragen.</p>
    <a href="/#premium" class="inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white font-semibold px-5 py-2.5 rounded-lg transition">Zur Warteliste</a>
  </div>
</body></html>"""


@router.get("/confirm/{token}", response_class=HTMLResponse)
async def confirm_lead(token: str, db: AsyncSession = Depends(get_db)):
    """Double-opt-in confirmation for DOI_SOURCES leads (premium-waitlist).

    Accepting GET (not POST) is intentional — the link is followed by a
    plain mail-client click. Tokens are single-use: confirmation_token is
    cleared once confirmed_at is set, so a second click of the same link
    falls through to the "invalid" page.
    """
    if not token or len(token) > 64:
        return HTMLResponse(_DOI_INVALID_HTML, status_code=400)

    result = await db.execute(
        select(Lead).where(Lead.confirmation_token == token)
    )
    lead = result.scalar_one_or_none()
    if lead is None:
        return HTMLResponse(_DOI_INVALID_HTML, status_code=404)

    lead.confirmed_at = datetime.now(timezone.utc)
    lead.confirmation_token = None
    await db.commit()
    logger.info(
        "DOI confirmed for lead %s (email=%s, source=%s)",
        lead.id, lead.email, lead.source,
    )
    return HTMLResponse(_DOI_CONFIRMED_HTML, status_code=200)
