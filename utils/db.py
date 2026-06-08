import os
from supabase import create_client, Client
from dotenv import load_dotenv
import bcrypt
from datetime import datetime, date, timedelta
import streamlit as st

load_dotenv()


@st.cache_resource
def get_supabase() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        st.error("Supabase credentials not found. Check your .streamlit/secrets.toml file.")
        st.stop()
    return create_client(url, key)


# ── Auth ──────────────────────────────────────────────────────────────────────

def create_user(email: str, password: str, name: str) -> dict | None:
    db = get_supabase()
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        res = db.table("users").insert({
            "email": email,
            "password_hash": pw_hash,
            "name": name,
        }).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"CREATE USER ERROR: {e}")
        return None

def login_user(email: str, password: str) -> dict | None:
    db = get_supabase()
    res = db.table("users").select("*").eq("email", email).execute()
    if not res.data:
        return None
    user = res.data[0]
    if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return user
    return None


# ── Family members ────────────────────────────────────────────────────────────

def get_family_members(user_id: str) -> list:
    db = get_supabase()
    res = db.table("family_members").select("*").eq("user_id", user_id).execute()
    return res.data or []


def create_family_member(user_id: str, name: str, relationship: str,
                          age: int | None, gender: str | None) -> dict | None:
    db = get_supabase()
    res = db.table("family_members").insert({
        "user_id": user_id,
        "name": name,
        "relationship": relationship,
        "age": age,
        "gender": gender,
    }).execute()
    return res.data[0] if res.data else None


def delete_family_member(member_id: str):
    db = get_supabase()
    db.table("family_members").delete().eq("id", member_id).execute()


# ── Medications ───────────────────────────────────────────────────────────────

def get_medications(family_member_id: str) -> list:
    db = get_supabase()
    res = (db.table("medications")
             .select("*")
             .eq("family_member_id", family_member_id)
             .eq("is_active", True)
             .execute())
    return res.data or []


def create_medication(family_member_id: str, name: str, dosage: str,
                       frequency: str, times_of_day: list[str],
                       start_date: date, end_date: date | None) -> dict | None:
    db = get_supabase()
    res = db.table("medications").insert({
        "family_member_id": family_member_id,
        "name": name,
        "dosage": dosage,
        "frequency": frequency,
        "times_of_day": times_of_day,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat() if end_date else None,
    }).execute()
    return res.data[0] if res.data else None


def deactivate_medication(med_id: str):
    db = get_supabase()
    db.table("medications").update({"is_active": False}).eq("id", med_id).execute()


# ── Reminders ─────────────────────────────────────────────────────────────────

def get_todays_reminders(family_member_id: str) -> list:
    """Return today's reminders for a family member with medication name joined."""
    db = get_supabase()
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    res = (db.table("reminders")
             .select("*, medications(name, dosage, family_member_id)")
             .gte("scheduled_time", today_start.isoformat())
             .lt("scheduled_time", today_end.isoformat())
             .execute())
    # Filter to this family member
    return [r for r in (res.data or [])
            if r.get("medications", {}).get("family_member_id") == family_member_id]


def confirm_reminder(reminder_id: str, status: str):
    """status: 'taken' or 'skipped'"""
    db = get_supabase()
    db.table("reminders").update({
        "status": status,
        "confirmed_at": datetime.now().isoformat(),
    }).eq("id", reminder_id).execute()


def get_adherence_stats(family_member_id: str, days: int = 7) -> dict:
    db = get_supabase()
    since = (datetime.now() - timedelta(days=days)).isoformat()
    res = (db.table("reminders")
             .select("status, medications(family_member_id)")
             .gte("scheduled_time", since)
             .execute())
    rows = [r for r in (res.data or [])
            if r.get("medications", {}).get("family_member_id") == family_member_id]
    total = len(rows)
    taken = sum(1 for r in rows if r["status"] == "taken")
    missed = sum(1 for r in rows if r["status"] == "missed")
    pending = sum(1 for r in rows if r["status"] == "pending")
    return {
        "total": total,
        "taken": taken,
        "missed": missed,
        "pending": pending,
        "rate": round((taken / total * 100) if total else 0, 1),
    }


# ── Scheduler helpers (used by worker) ───────────────────────────────────────

def generate_todays_reminders():
    """Called by scheduler at midnight — creates reminder rows for all active meds."""
    db = get_supabase()
    today = date.today()
    meds = (db.table("medications")
              .select("*")
              .eq("is_active", True)
              .lte("start_date", today.isoformat())
              .execute())
    created = 0
    for med in (meds.data or []):
        if med["end_date"] and date.fromisoformat(med["end_date"]) < today:
            continue
        for t in med["times_of_day"]:
            hour, minute = map(int, t.split(":"))
            scheduled = datetime.now().replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            # Avoid duplicates
            exists = (db.table("reminders")
                        .select("id")
                        .eq("medication_id", med["id"])
                        .gte("scheduled_time", today.isoformat())
                        .lt("scheduled_time", (today + timedelta(days=1)).isoformat())
                        .eq("status", "pending")
                        .execute())
            if not exists.data:
                db.table("reminders").insert({
                    "medication_id": med["id"],
                    "scheduled_time": scheduled.isoformat(),
                }).execute()
                created += 1
    return created


def get_overdue_unalerted_reminders(grace_minutes: int = 30) -> list:
    """Reminders past due + grace period, still pending, alert not yet sent."""
    db = get_supabase()
    cutoff = (datetime.now() - timedelta(minutes=grace_minutes)).isoformat()
    res = (db.table("reminders")
             .select("*, medications(name, dosage, family_member_id, family_members(name, user_id, users(email, name)))")
             .eq("status", "pending")
             .eq("alert_sent", False)
             .lt("scheduled_time", cutoff)
             .execute())
    return res.data or []


def mark_reminder_alerted(reminder_id: str):
    db = get_supabase()
    db.table("reminders").update({
        "status": "missed",
        "alert_sent": True,
    }).eq("id", reminder_id).execute()
