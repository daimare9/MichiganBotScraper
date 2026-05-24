import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from .models import Contract

logger = logging.getLogger(__name__)

# Badge colours per source
_BADGE_STYLES: dict[str, str] = {
    "MDOT": "background:#e8f4ea;color:#2e7d32;",
    "SIGMA": "background:#e3f2fd;color:#1565c0;",
}


def _build_html(contracts: list[Contract], keywords: list[str]) -> str:
    cards = ""
    for c in contracts:
        badge_style = _BADGE_STYLES.get(c.source, "background:#eee;color:#333;")
        value_row = (
            f'<span style="margin-right:16px;">💰 {c.estimated_value}</span>'
            if c.estimated_value
            else ""
        )
        county_row = (
            f'<span style="margin-right:16px;">📍 {c.county}</span>' if c.county else ""
        )
        letting_row = (
            f'<span style="margin-right:16px;">📅 Letting: {c.letting_date}</span>'
            if c.letting_date
            else ""
        )
        close_row = (
            f'<span style="margin-right:16px;">⏰ Closes: {c.close_date}</span>'
            if c.close_date
            else ""
        )

        cards += f"""
        <div style="border:1px solid #e0e0e0;border-radius:6px;padding:16px;
                    margin-bottom:16px;background:#fff;">
          <span style="display:inline-block;padding:2px 10px;border-radius:12px;
                       font-size:11px;font-weight:bold;{badge_style}">
            {c.source}
          </span>
          <h3 style="margin:10px 0 6px;">
            <a href="{c.url}" style="color:#1a3a5c;text-decoration:none;">{c.title}</a>
          </h3>
          <div style="color:#555;font-size:13px;margin-bottom:8px;">
            🏛️ {c.agency}
          </div>
          <div style="color:#777;font-size:12px;">
            {county_row}{value_row}{letting_row}{close_row}
            <span>📋 Posted: {c.post_date}</span>
          </div>
          <div style="margin-top:10px;">
            <a href="{c.url}"
               style="display:inline-block;padding:6px 14px;background:#1a3a5c;
                      color:#fff;border-radius:4px;font-size:13px;text-decoration:none;">
              View Bid →
            </a>
          </div>
        </div>
        """

    kw_list = ", ".join(f"<code>{k}</code>" for k in keywords)
    plural = "contract" if len(contracts) == 1 else "contracts"

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;">
  <div style="max-width:680px;margin:24px auto;border-radius:8px;
              overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.12);">

    <div style="background:#1a3a5c;color:#fff;padding:24px 30px;">
      <h1 style="margin:0;font-size:20px;">
        🏗️ {len(contracts)} New Michigan Concrete {plural.title()} Found
      </h1>
      <p style="margin:6px 0 0;opacity:.8;font-size:13px;">
        Michigan Bot Scraper — real-time construction contract alerts
      </p>
    </div>

    <div style="padding:24px 30px;">
      <p style="color:#555;font-size:14px;margin-top:0;">
        The following bid(s) matched your keywords: {kw_list}
      </p>
      {cards}
    </div>

    <div style="background:#f9f9f9;padding:14px 30px;border-top:1px solid #eee;
                font-size:11px;color:#aaa;">
      Michigan Bot Scraper &nbsp;|&nbsp; Sources: MDOT Bid Letting &amp; SIGMA VSS
      &nbsp;|&nbsp; Edit keywords in <code>config/keywords.yaml</code>
    </div>
  </div>
</body></html>"""


def send_alert(contracts: list[Contract], config: dict[str, Any]) -> None:
    """Send an HTML email listing all newly found contracts."""
    if not contracts:
        return

    plural = "Contract" if len(contracts) == 1 else "Contracts"
    subject = f"🏗️ {len(contracts)} New Michigan Concrete {plural} — Act Now"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config["gmail_user"]
    msg["To"] = config["recipient_email"]

    html_body = _build_html(contracts, config["keywords"])
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    logger.info("Connecting to Gmail SMTP…")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(config["gmail_user"], config["gmail_app_password"])
        smtp.send_message(msg)

    logger.info("Alert email sent to %s", config["recipient_email"])
