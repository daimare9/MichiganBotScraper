import logging
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from .models import Contract

logger = logging.getLogger(__name__)

# Badge colours per source
_BADGE_STYLES: dict[str, str] = {
    "MDOT": "background:#e8f4ea;color:#2e7d32;border:1px solid #a5d6a7;",
    "SIGMA": "background:#e3f2fd;color:#1565c0;border:1px solid #90caf9;",
}

_BUTTON_LABELS: dict[str, str] = {
    "MDOT": "View PDF →",
    "SIGMA": "View Solicitation →",
}


def _highlight_keywords(text: str, keywords: list[str]) -> str:
    """Wrap any keyword match in a yellow highlight span."""
    if not text or not keywords:
        return text
    pattern = re.compile(
        r"(" + "|".join(re.escape(k) for k in keywords) + r")",
        re.IGNORECASE,
    )
    return pattern.sub(
        r'<mark style="background:#fff176;padding:0 2px;border-radius:2px;">\1</mark>',
        text,
    )


def _summary_rows(contracts: list[Contract]) -> str:
    rows = ""
    for i, c in enumerate(contracts, 1):
        date_cell = c.letting_date or c.close_date or c.post_date or "—"
        date_label = (
            "Letting" if c.letting_date else ("Closes" if c.close_date else "Posted")
        )
        badge_style = _BADGE_STYLES.get(c.source, "background:#eee;color:#333;")
        rows += f"""
        <tr style="border-bottom:1px solid #f0f0f0;">
          <td style="padding:8px 6px;color:#888;font-size:12px;">{i}</td>
          <td style="padding:8px 6px;">
            <span style="display:inline-block;padding:1px 8px;border-radius:10px;
                         font-size:10px;font-weight:bold;{badge_style}">
              {c.source}
            </span>
          </td>
          <td style="padding:8px 6px;font-size:13px;">
            <a href="{c.url}" style="color:#1a3a5c;text-decoration:none;font-weight:500;">
              {c.title}
            </a>
          </td>
          <td style="padding:8px 6px;font-size:12px;color:#666;white-space:nowrap;">
            {date_label}: {date_cell}
          </td>
          <td style="padding:8px 6px;">
            <a href="{c.url}"
               style="white-space:nowrap;padding:4px 10px;background:#1a3a5c;color:#fff;
                      border-radius:4px;font-size:11px;text-decoration:none;">
              Open ↗
            </a>
          </td>
        </tr>"""
    return rows


def _build_html(contracts: list[Contract], keywords: list[str]) -> str:
    cards = ""
    for c in contracts:
        badge_style = _BADGE_STYLES.get(c.source, "background:#eee;color:#333;")
        btn_label = _BUTTON_LABELS.get(c.source, "View Bid →")

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

        # Description excerpt with keyword highlighting
        desc_block = ""
        if c.description:
            excerpt = c.description[:350].strip()
            if len(c.description) > 350:
                excerpt += "…"
            highlighted = _highlight_keywords(excerpt, keywords)
            desc_block = f"""
          <div style="margin:10px 0;padding:10px 12px;background:#f8f9fa;border-left:3px solid #ccc;
                      font-size:13px;color:#444;line-height:1.5;border-radius:0 4px 4px 0;">
            {highlighted}
          </div>"""

        cards += f"""
        <div style="border:1px solid #e0e0e0;border-radius:8px;padding:18px 20px;
                    margin-bottom:20px;background:#fff;
                    box-shadow:0 1px 4px rgba(0,0,0,.06);">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
            <span style="display:inline-block;padding:2px 10px;border-radius:12px;
                         font-size:11px;font-weight:bold;{badge_style}">
              {c.source}
            </span>
            <span style="color:#999;font-size:11px;">ID: {c.contract_id}</span>
          </div>
          <h3 style="margin:0 0 4px;">
            <a href="{c.url}" style="color:#1a3a5c;text-decoration:none;">{c.title}</a>
          </h3>
          <div style="color:#666;font-size:13px;margin-bottom:6px;">
            🏛️ {c.agency}
          </div>
          {desc_block}
          <div style="color:#777;font-size:12px;margin-top:10px;line-height:2;">
            {county_row}{value_row}{letting_row}{close_row}
            <span>📋 Posted: {c.post_date}</span>
          </div>
          <div style="margin-top:14px;">
            <a href="{c.url}"
               style="display:inline-block;padding:8px 18px;background:#1a3a5c;
                      color:#fff;border-radius:5px;font-size:13px;
                      text-decoration:none;font-weight:600;letter-spacing:.3px;">
              {btn_label}
            </a>
          </div>
        </div>
        """

    kw_list = ", ".join(f"<code>{k}</code>" for k in keywords)
    plural = "contract" if len(contracts) == 1 else "contracts"
    summary_rows = _summary_rows(contracts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:Arial,sans-serif;">
  <div style="max-width:700px;margin:28px auto;border-radius:10px;
              overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,.14);">

    <!-- Header -->
    <div style="background:#1a3a5c;color:#fff;padding:26px 32px;">
      <h1 style="margin:0;font-size:22px;font-weight:700;">
        🏗️ {len(contracts)} New Michigan Concrete {plural.title()} Found
      </h1>
      <p style="margin:8px 0 0;opacity:.75;font-size:13px;">
        Michigan Bot Scraper &mdash; real-time construction contract alerts
      </p>
    </div>

    <!-- Quick-scan summary table -->
    <div style="background:#fff;padding:20px 32px;border-bottom:1px solid #e8e8e8;">
      <p style="margin:0 0 12px;font-size:13px;color:#555;">
        Matched keywords: {kw_list}
      </p>
      <table style="width:100%;border-collapse:collapse;">
        <thead>
          <tr style="border-bottom:2px solid #e8e8e8;">
            <th style="padding:6px;text-align:left;font-size:11px;color:#999;
                       text-transform:uppercase;">#</th>
            <th style="padding:6px;text-align:left;font-size:11px;color:#999;
                       text-transform:uppercase;">Source</th>
            <th style="padding:6px;text-align:left;font-size:11px;color:#999;
                       text-transform:uppercase;">Title</th>
            <th style="padding:6px;text-align:left;font-size:11px;color:#999;
                       text-transform:uppercase;">Date</th>
            <th style="padding:6px;"></th>
          </tr>
        </thead>
        <tbody>{summary_rows}</tbody>
      </table>
    </div>

    <!-- Detail cards -->
    <div style="padding:24px 32px;background:#f0f2f5;">
      <p style="margin:0 0 20px;font-size:12px;color:#999;text-transform:uppercase;
                letter-spacing:.5px;">Full Details</p>
      {cards}
    </div>

    <!-- Footer -->
    <div style="background:#fff;padding:16px 32px;border-top:1px solid #eee;
                font-size:11px;color:#bbb;line-height:1.8;">
      Michigan Bot Scraper &nbsp;|&nbsp;
      Sources: MDOT Bid Letting &amp; SIGMA VSS &nbsp;|&nbsp;
      Edit keywords in <code>config/keywords.yaml</code>
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
