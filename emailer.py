import os, smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from html import escape


def render_html(jobs) -> str:
    rows = []
    for j in jobs:
        rows.append(f"""
        <div style="border:1px solid #e5e7eb;border-radius:8px;padding:14px;margin-bottom:12px;font-family:system-ui,sans-serif">
          <div style="font-size:16px;font-weight:600">{escape(j['title'])}</div>
          <div style="color:#4b5563;margin:4px 0">{escape(j['company'] or '—')} · {escape(j['location'])}</div>
          <div style="font-size:12px;color:#059669;background:#ecfdf5;display:inline-block;
                      padding:2px 8px;border-radius:4px;margin-bottom:8px">
            Match {j['score']}/10 — {escape(j['reason'] or '')}
          </div>
          <div><a href="{escape(j['url'])}" style="color:#2563eb">View listing →</a></div>
          <div style="font-size:11px;color:#9ca3af;margin-top:6px">source: {escape(j['source'])}</div>
        </div>""")
    return f"""<div style="max-width:640px;margin:auto">
      <h2 style="font-family:system-ui,sans-serif">{len(jobs)} new role{'s' if len(jobs)!=1 else ''}</h2>
      {''.join(rows)}
    </div>"""


def render_text(jobs) -> str:
    """Plain-text fallback — helps deliverability a lot."""
    lines = [f"{len(jobs)} new role(s)\n"]
    for j in jobs:
        lines.append(
            f"- {j['title']} @ {j['company'] or '—'} ({j['location']})\n"
            f"  Match {j['score']}/10 — {j['reason'] or ''}\n"
            f"  {j['url']}\n"
        )
    return "\n".join(lines)


def send(subject: str, html: str, text: str = ""):
    user = os.environ["GMAIL_USER"]           # full address, e.g. you@gmail.com
    password = os.environ["GMAIL_APP_PASSWORD"]
    to_addr = os.environ["TO_EMAIL"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"JobBot <{user}>"
    msg["To"] = to_addr

    # text first, html second — mail clients pick the last one they understand
    if text:
        msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=30) as server:
        server.login(user, password)
        server.sendmail(user, [to_addr], msg.as_string())
    print(f"Email sent to {to_addr}")