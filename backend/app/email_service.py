"""Email service — sends report PDF to user via SMTP (multipart HTML + plaintext)."""

import logging
from email.message import EmailMessage
from html import escape

import aiosmtplib

from app.config import get_settings
from app.email_logo import get_header_png

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ihr Bodenbericht</title>
<style>
  /* Global resets for mail clients */
  body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
  table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
  img {{ -ms-interpolation-mode: bicubic; border: 0; outline: none; text-decoration: none; }}
  body {{ margin: 0; padding: 0; width: 100% !important; height: 100% !important; background: #f3f4f6; }}
  a {{ color: #15803d; text-decoration: underline; }}
  /* Typography */
  .body-bg {{ background: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; color: #1f2937; }}
  .container {{ width: 600px; max-width: 100%; background: #ffffff; }}
  .header {{ background: #0c1d3a; padding: 0; }}
  .header img {{ display: block; width: 600px; max-width: 100%; height: auto; }}
  .content {{ padding: 40px 44px 32px 44px; }}
  h1.title {{ font-size: 24px; font-weight: 700; color: #0c1d3a; margin: 0 0 20px 0; letter-spacing: -0.01em; line-height: 1.3; }}
  p {{ font-size: 15px; line-height: 1.6; color: #1f2937; margin: 0 0 16px 0; }}
  p.muted {{ color: #6b7280; font-size: 14px; }}
  .address {{
    background: #f9fafb; border-left: 3px solid #16a34a;
    padding: 14px 18px; border-radius: 6px;
    font-size: 15px; color: #0c1d3a; font-weight: 500;
    margin: 4px 0 24px 0;
  }}
  .info-box {{
    background: #f0fdf4; border: 1px solid #bbf7d0;
    border-radius: 8px; padding: 18px 22px;
    margin: 28px 0;
  }}
  .info-box h3 {{
    font-size: 14px; font-weight: 600; color: #15803d;
    margin: 0 0 10px 0; text-transform: uppercase; letter-spacing: 0.05em;
  }}
  .info-box ul {{ margin: 0; padding: 0 0 0 18px; }}
  .info-box li {{ font-size: 14px; line-height: 1.6; color: #1f2937; margin-bottom: 4px; }}
  .disclaimer {{
    font-size: 13px; line-height: 1.55; color: #6b7280;
    padding: 20px 0 0 0; margin: 16px 0 0 0;
    border-top: 1px solid #e5e7eb;
  }}
  .footer {{
    background: #f9fafb;
    padding: 28px 44px;
    font-size: 12px; line-height: 1.6; color: #6b7280;
    border-top: 1px solid #e5e7eb;
  }}
  .footer a {{ color: #6b7280; text-decoration: underline; }}
  .footer .brand {{ color: #0c1d3a; font-weight: 600; font-size: 13px; }}
  @media (max-width: 600px) {{
    .container {{ width: 100% !important; }}
    .content, .footer {{ padding-left: 24px !important; padding-right: 24px !important; }}
    h1.title {{ font-size: 22px !important; }}
  }}
</style>
</head>
<body class="body-bg">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="body-bg">
  <tr>
    <td align="center" style="padding: 24px 12px;">
      <table role="presentation" class="container" cellpadding="0" cellspacing="0" border="0" style="border-radius: 10px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">

        <!-- Header with inlined logo banner -->
        <tr>
          <td class="header">
            <img src="cid:bodenbericht-logo" alt="Bodenbericht" width="600" style="display: block; width: 100%; max-width: 600px; height: auto;">
          </td>
        </tr>

        <!-- Main content -->
        <tr>
          <td class="content">
            <h1 class="title">Ihr Bodenbericht ist fertig.</h1>
            <p>Guten Tag,</p>
            <p>vielen Dank fuer Ihre Anfrage. Fuer den folgenden Standort haben wir Ihren kostenlosen Bodenbericht erstellt:</p>
            <div class="address">{address}</div>
            <p>Den Bericht finden Sie als PDF im Anhang dieser E-Mail.</p>

            <div class="info-box">
              <h3>Was im Bericht steht</h3>
              <ul>
                <li>Ampel-Einstufung Ihres Standorts</li>
                <li>Bodenbewegungs-Messpunkte aus dem Copernicus European Ground Motion Service</li>
                <li>Bodenqualitaet (pH, Naehrstoffe, Textur) aus ISRIC SoilGrids und JRC LUCAS</li>
                <li>Einordnung im regionalen und landesweiten Vergleich</li>
              </ul>
            </div>

            <p>Rueckfragen? Antworten Sie einfach auf diese E-Mail oder schreiben Sie an <a href="mailto:team@geoforensic.de">team@geoforensic.de</a>.</p>

            <p style="margin-top: 28px;">Mit freundlichen Gruessen<br>Ihr Bodenbericht-Team</p>

            <p class="disclaimer">
              <strong style="color: #4b5563;">Hinweis:</strong>
              Dieser Bericht ist ein automatisiertes Datenscreening auf Basis oeffentlich verfuegbarer EU-Satelliten- und Bodendaten. Er ersetzt keine fachliche Einzelfallbewertung durch eine sachverstaendige Person.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td class="footer">
            <p style="margin: 0 0 8px 0;"><span class="brand">Bodenbericht</span> &middot; Ein Service der Tepnosholding GmbH</p>
            <p style="margin: 0 0 12px 0;">
              <a href="https://bodenbericht.de/impressum.html">Impressum</a> &middot;
              <a href="https://bodenbericht.de/datenschutz.html">Datenschutz</a> &middot;
              <a href="https://bodenbericht.de/datenquellen.html">Datenquellen</a>
            </p>
            <p style="margin: 0; font-size: 11px; color: #9ca3af;">
              Generated using European Union&rsquo;s Copernicus Land Monitoring Service information.
            </p>
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>
</body>
</html>"""


def _build_html_body(address: str) -> str:
    return _HTML_TEMPLATE.format(address=escape(address))


def _build_text_body(address: str) -> str:
    """Plaintext fallback for mail clients that do not render HTML."""
    return (
        f"Guten Tag,\n\n"
        f"Ihr kostenloser Bodenbericht fuer\n"
        f"{address}\n"
        f"ist fertig. Das PDF finden Sie im Anhang.\n\n"
        f"Der Bericht ist ein automatisiertes Datenscreening auf Basis oeffentlicher "
        f"EU-Satelliten- und Bodendaten (Copernicus EGMS, ISRIC SoilGrids, JRC LUCAS). "
        f"Er ersetzt keine fachliche Einzelfallbewertung durch eine sachverstaendige Person.\n\n"
        f"Bei Rueckfragen erreichen Sie uns unter team@geoforensic.de.\n\n"
        f"Mit freundlichen Gruessen\n"
        f"Ihr Bodenbericht-Team\n\n"
        f"---\n"
        f"Bodenbericht · Ein Service der Tepnosholding GmbH\n"
        f"https://bodenbericht.de/impressum.html · https://bodenbericht.de/datenschutz.html\n"
        f"Generated using European Union's Copernicus Land Monitoring Service information."
    )


# ---------------------------------------------------------------------------
# Sender
# ---------------------------------------------------------------------------

async def send_report_email(
    recipient_email: str,
    report_address: str,
    pdf_bytes: bytes,
    report_id: str,
) -> bool:
    """Send a report PDF as multipart HTML+plaintext email. Returns True on success."""
    if not settings.smtp_host:
        logger.warning("SMTP not configured — skipping email for report %s", report_id)
        return False

    msg = EmailMessage()
    msg["Subject"] = f"Ihr Bodenbericht für {report_address}"
    from_name = getattr(settings, "smtp_from_name", "Bodenbericht")
    msg["From"] = f"{from_name} <{settings.smtp_from_email}>"
    msg["To"] = recipient_email
    msg["Reply-To"] = "team@geoforensic.de"

    # Plaintext first, then HTML as alternative.
    msg.set_content(_build_text_body(report_address))
    msg.add_alternative(_build_html_body(report_address), subtype="html")

    # Attach the inline logo to the HTML part (not the plaintext part).
    # The HTML alternative is the LAST entry in the payload after set_content + add_alternative.
    html_part = msg.get_payload()[-1]
    try:
        html_part.add_related(
            get_header_png(),
            maintype="image",
            subtype="png",
            cid="<bodenbericht-logo>",
            filename="bodenbericht-logo.png",
        )
    except Exception:
        logger.exception("Failed to embed email logo — sending without header image")

    # PDF attachment.
    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=f"bodenbericht-{report_id}.pdf",
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
