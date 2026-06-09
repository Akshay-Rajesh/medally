"""
Scheduler that runs as a background thread inside Streamlit.
Import and call start_scheduler() once from app.py
"""
import threading
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apscheduler.schedulers.background import BackgroundScheduler

log = logging.getLogger(__name__)
_scheduler = None


def job_generate_reminders():
    from utils.db import generate_todays_reminders
    count = generate_todays_reminders()
    log.info(f"Generated {count} reminders")


def job_check_missed():
    from utils.db import get_overdue_unalerted_reminders, mark_reminder_alerted
    from utils.email import send_missed_medication_alert
    overdue = get_overdue_unalerted_reminders(grace_minutes=30)
    for reminder in overdue:
        try:
            med = reminder.get("medications", {})
            member = med.get("family_members", {})
            user = member.get("users", {})
            sent = send_missed_medication_alert(
                to_email=user.get("email"),
                caregiver_name=user.get("name", "Caregiver"),
                patient_name=member.get("name", "Family member"),
                medication_name=f"{med.get('name', '')} {med.get('dosage', '')}".strip(),
                scheduled_time=datetime.fromisoformat(
                    reminder["scheduled_time"]
                ).strftime("%I:%M %p"),
            )
            if sent:
                mark_reminder_alerted(reminder["id"])
                log.info(f"Alert sent for reminder {reminder['id']}")
        except Exception as e:
            log.error(f"Error: {e}")


def start_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        return  # already running, don't start twice
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(job_generate_reminders, "cron", hour=0, minute=0)
    _scheduler.add_job(job_check_missed, "interval", minutes=5)
    _scheduler.start()
    # Seed today's reminders immediately on startup
    job_generate_reminders()
    log.info("Scheduler started")

if __name__ == "__main__":
    if "--once" in sys.argv:
        log.info("Running in --once mode")
        job_generate_reminders()
        job_check_missed()