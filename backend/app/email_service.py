"""Email service — sends report PDF to user after purchase."""

import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_report_email(
    recipient_email: str,
    report_address: str,
    pdf_bytes: bytes,
    report_id: str,
) -> bool:
    """Send a report PDF as email attachment. Returns True on success."""
    if not settings.smtp_host:
        logger.warning("SMTP not configured — skipping email for report %s", report_id)
        return False

    msg = EmailMessage()
    msg["Subject"] = f"GeoForensic Standortauskunft — {report_address}"
    msg["From"] = settings.smtp_from_email
    msg["To"] = recipient_email

    msg.set_content(
        f"Guten Tag,\n\n"
        f"Ihr Bodenbewegungsscreening für {report_address} ist fertig.\n"
        f"Das PDF finden Sie im Anhang.\n\n"
        f"Mit freundlichen Grüßen,\n"
        f"GeoForensic\n\n"
        f"---\n"
        f"Diese Standortauskunft ist ein automatisiertes Datenscreening "
        f"und ersetzt keine fachliche Einzelfallbewertung.\n"
        f"Generated using European Union's Copernicus Land Monitoring Service information."
    )

    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=f"geoforensic-{report_id}.pdf",
    )

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=True,
        )
        logger.info("Report email sent to %s for report %s", recipient_email, report_id)
        return True
    except Exception:
        logger.exception("Failed to send report email for %s", report_id)
        return False
