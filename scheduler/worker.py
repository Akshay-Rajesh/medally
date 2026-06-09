import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Must configure logging before anything else
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout
)
log = logging.getLogger(__name__)

_scheduler = None


def job_generate_reminders():
    from utils.db import generate_todays_reminders
    count = generate_todays_reminders()
    log.info(f"Generated {count} reminders")


def job_check_missed():
    from utils.db import get_overdue_unalerted_reminders, mark_reminder_alerted
    from utils.email import send_missed_medication_alert
    log.info("Checking for missed doses...")
    overdue = get_overdue_unalerted_reminders(grace_minutes=30)
    log.info(f"Found {len(overdue)} overdue reminder(s)")
    for reminder in overdue:
        try:
            med = reminder.get("medications", {})
            member = med.get("family_members", {})
            user = member.get("users", {})
            log.info(f"Sending alert to {user.get('email')} for {member.get('name')}")
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
                log.info(f"Alert sent successfully for reminder {reminder['id']}")
            else:
                log.error(f"Failed to send alert for reminder {reminder['id']}")
        except Exception as e:
            log.error(f"Error processing reminder: {e}")


def start_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    from apscheduler.schedulers.background import BackgroundScheduler
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(job_generate_reminders, "cron", hour=0, minute=0)
    _scheduler.add_job(job_check_missed, "interval", minutes=5)
    _scheduler.start()
    job_generate_reminders()
    log.info("Scheduler started")


if __name__ == "__main__":
    if "--once" in sys.argv:
        log.info("=== Running in --once mode ===")
        job_generate_reminders()
        job_check_missed()
        log.info("=== Done ===")