import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _get_creds():
    try:
        import streamlit as st
        return st.secrets["GMAIL_ADDRESS"], st.secrets["GMAIL_APP_PASSWORD"]
    except Exception:
        return os.environ.get("GMAIL_ADDRESS", ""), os.environ.get("GMAIL_APP_PASSWORD", "")


def _send(to_email: str, subject: str, html: str) -> bool:
    gmail, app_password = _get_creds()
    if not gmail or not app_password:
        print("Gmail credentials not configured")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"MedAlly <{gmail}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail, app_password)
            server.sendmail(gmail, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


def send_missed_medication_alert(to_email, caregiver_name, patient_name, medication_name, scheduled_time):
    html = f"""
    <div style="font-family:sans-serif;max-width:500px;padding:24px">
      <h2 style="color:#c0392b">Missed medication alert</h2>
      <p>Hi {caregiver_name},</p>
      <p><strong>{patient_name}</strong> has not confirmed taking
      <strong>{medication_name}</strong> scheduled for <strong>{scheduled_time}</strong>.</p>
      <div style="background:#fdf3f3;border-left:4px solid #c0392b;padding:16px;border-radius:4px;margin:20px 0">
        <p style="margin:0;color:#c0392b;font-weight:600">Action needed</p>
        <p style="margin:8px 0 0;color:#555;font-size:14px">Please check in with {patient_name}.</p>
      </div>
      <p style="color:#999;font-size:12px">— MedAlly</p>
    </div>
    """
    return _send(to_email, f"⚠️ {patient_name} missed their medication", html)


def send_welcome_email(to_email: str, name: str):
    html = f"""
    <div style="font-family:sans-serif;max-width:500px;padding:24px">
      <h2 style="color:#2c3e50">Welcome to MedAlly, {name}! 💊</h2>
      <p>Add your family members and their medications.</p>
      <p>We'll alert you if anyone misses a dose.</p>
      <p style="color:#999;font-size:12px">— MedAlly</p>
    </div>
    """
    return _send(to_email, "Welcome to MedAlly 💊", html)