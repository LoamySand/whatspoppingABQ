"""
Email notification utilities for pipeline alerts.
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def get_email_config():
    """Get email configuration from environment."""
    email = os.getenv('ALERT_EMAIL')
    password = os.getenv('GMAIL_APP_PASSWORD')
    if not email or not password:
        raise ValueError(
            "ALERT_EMAIL and GMAIL_APP_PASSWORD must be set in .env"
        )
    return email, password


def send_email(subject: str, body: str, is_html: bool = False):
    """
    Send an email via Gmail SMTP.

    Args:
        subject: Email subject line
        body: Email body content
        is_html: Whether body is HTML (default False)
    """
    try:
        email, password = get_email_config()

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = email
        msg['To'] = email

        part = MIMEText(body, 'html' if is_html else 'plain')
        msg.attach(part)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(email, password)
            server.sendmail(email, email, msg.as_string())

        logger.info(f"Alert email sent: {subject}")

    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")


def send_failure_alert(flow_name: str, error: str, run_name: str = None):
    """Send a pipeline failure alert email."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    subject = f" Pipeline Failed: {flow_name}"

    body = f"""
    <h2 style="color: #cc0000;">Pipeline Failure Alert</h2>
    <p><strong>Flow:</strong> {flow_name}</p>
    <p><strong>Run:</strong> {run_name or 'Unknown'}</p>
    <p><strong>Time:</strong> {timestamp}</p>
    <hr>
    <h3>Error:</h3>
    <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{error}</pre>
    <hr>
    <p>Check the Prefect UI for full details.</p>
    """
    send_email(subject, body, is_html=True)


def send_success_digest(flow_name: str, stats: dict):
    """Send a daily success digest email."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    subject = f" Daily Pipeline Success: {flow_name}"

    # Build stats rows
    stats_rows = ""
    for key, value in stats.items():
        label = key.replace('_', ' ').title()
        stats_rows += f"""
        <tr>
            <td style="padding: 6px 12px; border-bottom: 1px solid #eee;">
                {label}
            </td>
            <td style="padding: 6px 12px; border-bottom: 1px solid #eee;">
                <strong>{value}</strong>
            </td>
        </tr>"""

    body = f"""
    <h2 style="color: #2e7d32;">Daily Pipeline Success</h2>
    <p><strong>Flow:</strong> {flow_name}</p>
    <p><strong>Completed:</strong> {timestamp}</p>
    <hr>
    <h3>Run Statistics:</h3>
    <table style="border-collapse: collapse; width: 100%;">
        {stats_rows}
    </table>
    <hr>
    <p style="color: #666; font-size: 12px;">
        This is your daily digest. If you stop receiving these, 
        the pipeline has stopped running.
    </p>
    """
    send_email(subject, body, is_html=True)


def send_crash_alert(flow_name: str, details: str = None):
    """Send a pipeline crash/timeout alert email."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    subject = f" Pipeline Crashed: {flow_name}"

    body = f"""
    <h2 style="color: #cc0000;">Pipeline Crash Alert</h2>
    <p><strong>Flow:</strong> {flow_name}</p>
    <p><strong>Time:</strong> {timestamp}</p>
    <hr>
    <p>{details or 'The flow crashed or timed out unexpectedly.'}</p>
    <hr>
    <p>Check the Prefect UI and system logs for details.</p>
    <p>SSH into the Pi and run:<br>
    <code>journalctl -u prefect-worker -n 50</code></p>
    """
    send_email(subject, body, is_html=True)