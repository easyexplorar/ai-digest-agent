"""Convert markdown digest to PDF and send via email."""

import base64
import smtplib
import ssl
import tempfile
from email.message import EmailMessage
from pathlib import Path

import markdown
from xhtml2pdf import pisa

LOGO_PATH = Path(r"REDACTED_LOGO_PATH")

DISCLAIMER = (
    "Confidential — REDACTED_BRAND internal only. "
    "This report is AI-generated and may contain inaccuracies. "
    "Not intended for external distribution."
)

PDF_CSS = """
@page { margin: 2cm; }
body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.7;
    color: #1a1a1a;
}

/* ── Branded header ───────────────────────────── */
.header-table { width: 100%; border-bottom: 2.5px solid #0099cc; padding-bottom: 10px; margin-bottom: 24px; }
.logo-cell { width: 220px; vertical-align: middle; }
.logo-cell img { height: 60pt; width: auto; }
.logo-text { font-size: 15pt; font-weight: bold; color: #0099cc; letter-spacing: 1px; }
.title-cell { vertical-align: middle; padding-left: 14px; }
.report-title { font-size: 15pt; font-weight: bold; color: #0d1b2a; letter-spacing: 0.3px; }
.report-meta { font-size: 8.5pt; color: #777777; margin-top: 3px; }

/* ── Section headings ─────────────────────────── */
h1 { font-size: 13pt; color: #0099cc; margin-top: 20px; margin-bottom: 8px; }
h2 {
    font-size: 12pt;
    font-weight: bold;
    color: #ffffff;
    background-color: #0d1b2a;
    padding: 6px 12px;
    margin-top: 28px;
    margin-bottom: 12px;
}
h3 {
    font-size: 10.5pt;
    font-weight: bold;
    color: #0d1b2a;
    background-color: #e8f4fc;
    border-left: 4px solid #0099cc;
    padding: 6px 10px;
    margin-top: 18px;
    margin-bottom: 8px;
}
strong { color: #0d1b2a; }
em { color: #555555; }

/* ── Body elements ────────────────────────────── */
ul { margin-left: 16px; margin-top: 6px; margin-bottom: 10px; }
li { margin-bottom: 8px; line-height: 1.6; }
p { margin-top: 0px; margin-bottom: 10px; }
hr { border: none; border-top: 1px solid #d0dde8; margin: 18px 0; }
a { color: #0077aa; }
code { font-size: 9pt; background-color: #f0f0f0; padding: 1px 3px; }

/* ── Disclaimer footer ────────────────────────── */
.disclaimer {
    margin-top: 32px;
    border-top: 1px solid #cccccc;
    padding-top: 8px;
    font-size: 7.5pt;
    color: #999999;
    font-style: italic;
}
"""


_LOGO_TARGET_HEIGHT_PX = 360  # 60pt (~120px at 144dpi) × 3× for crisp PDF rendering


def _logo_html() -> str:
    if LOGO_PATH.exists():
        try:
            import io
            from PIL import Image
            img = Image.open(LOGO_PATH).convert("RGBA")
            ratio = _LOGO_TARGET_HEIGHT_PX / img.height
            new_w = max(1, int(img.width * ratio))
            img = img.resize((new_w, _LOGO_TARGET_HEIGHT_PX), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            data = base64.b64encode(buf.getvalue()).decode()
        except Exception:
            data = base64.b64encode(LOGO_PATH.read_bytes()).decode()
        uri = f"data:image/png;base64,{data}"
        return f'<td class="logo-cell"><img src="{uri}" /></td>'
    return '<td class="logo-cell"><span class="logo-text">REDACTED_BRAND</span></td>'


def _normalise_lists(text: str) -> str:
    """Ensure inline '- item - item' patterns are split to one bullet per line."""
    import re
    # Split lines that contain multiple '- ' list items run together
    lines = []
    for line in text.splitlines():
        # If a line has ' - ' mid-sentence (not at the start), split it into separate list lines
        if re.search(r'\S.*\s-\s', line) and not line.lstrip().startswith('#'):
            parts = re.split(r'\s+-\s+', line)
            for i, part in enumerate(parts):
                part = part.strip()
                if not part:
                    continue
                if i == 0 and not line.lstrip().startswith('-'):
                    lines.append(part)
                else:
                    lines.append(f'- {part}')
        else:
            lines.append(line)
    return '\n'.join(lines)


def md_to_pdf(md_text: str, output_path: Path, date_label: str = "", report_type: str = "Daily Intelligence Report") -> bool:
    body_html = markdown.markdown(_normalise_lists(md_text), extensions=["extra", "smarty"])
    meta = f"{date_label}&nbsp;&nbsp;|&nbsp;&nbsp;{report_type}" if date_label else report_type

    full_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>{PDF_CSS}</style></head>
<body>

<table class="header-table" cellpadding="0" cellspacing="0">
  <tr>
    {_logo_html()}
    <td class="title-cell">
      <div class="report-title">AI Discipline Pulse</div>
      <div class="report-meta">{meta}</div>
    </td>
  </tr>
</table>

{body_html}

<div class="disclaimer">{DISCLAIMER}</div>
</body>
</html>"""

    with open(output_path, "wb") as f:
        status = pisa.CreatePDF(full_html, dest=f)
    return not status.err


def send_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    to_addr: str,
    subject: str,
    body_text: str,
    pdf_path: Path,
) -> bool:
    """Send one message per recipient in `to_addr` (comma-separated) so each
    person's inbox only shows their own address in the To: header, never the
    other recipients'."""
    recipients = [addr.strip() for addr in to_addr.split(",") if addr.strip()]
    pdf_bytes = pdf_path.read_bytes()

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls(context=ctx)
        server.login(smtp_user, smtp_pass)
        for recipient in recipients:
            msg = EmailMessage()
            msg["From"] = smtp_user
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.set_content(body_text)
            msg.add_attachment(
                pdf_bytes,
                maintype="application",
                subtype="pdf",
                filename=pdf_path.name,
            )
            server.send_message(msg)
    return True


def send_digest_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    to_addr: str,
    digest_text: str,
    date_label: str,
) -> bool:
    """Convert daily digest to PDF and email it."""
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / f"ai_digest_{date_label}.pdf"
        if not md_to_pdf(digest_text, pdf_path, date_label=date_label, report_type="Daily Intelligence Report"):
            return False
        return send_email(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_pass=smtp_pass,
            to_addr=to_addr,
            subject=f"AI Discipline Pulse — {date_label}",
            body_text="Your daily AI digest is attached as a PDF.",
            pdf_path=pdf_path,
        )


def send_rollup_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    to_addr: str,
    rollup_text: str,
    week_label: str,
) -> bool:
    """Convert weekly rollup to PDF and email it."""
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / f"weekly_rollup_{week_label}.pdf"
        if not md_to_pdf(rollup_text, pdf_path, date_label=week_label, report_type="Weekly Rollup"):
            return False
        return send_email(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_pass=smtp_pass,
            to_addr=to_addr,
            subject=f"AI Weekly Rollup — {week_label}",
            body_text="Your weekly AI rollup is attached as a PDF.",
            pdf_path=pdf_path,
        )
