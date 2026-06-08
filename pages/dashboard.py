import streamlit as st
from datetime import datetime
from utils.session import get_user
from utils.db import (
    get_family_members,
    get_todays_reminders,
    confirm_reminder,
    get_adherence_stats,
)

STATUS_EMOJI = {
    "pending": "⏳",
    "taken": "✅",
    "skipped": "⏭️",
    "missed": "❌",
}

STATUS_COLOR = {
    "pending": "#f0ad4e",
    "taken": "#5cb85c",
    "skipped": "#aaa",
    "missed": "#d9534f",
}


def render():
    user = get_user()
    now = datetime.now()
    st.markdown(f"## 🏠 Today's medications")
    st.markdown(
        f"<span style='color:#888;font-size:14px'>"
        f"{now.strftime('%A, %B %d %Y')}"
        f"</span>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    members = get_family_members(user["id"])
    if not members:
        st.info("Welcome! Start by adding your family members and their medications.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👨‍👩‍👧 Add family member", use_container_width=True):
                st.session_state.page = "family"
                st.rerun()
        return

    # ── Per-member reminder cards ─────────────────────────────────────────────
    any_reminders = False
    for member in members:
        reminders = get_todays_reminders(member["id"])
        if not reminders:
            continue

        any_reminders = True
        st.markdown(f"### {member['name']}")

        for r in sorted(reminders, key=lambda x: x["scheduled_time"]):
            med = r.get("medications", {})
            med_name = med.get("name", "Unknown")
            dosage = med.get("dosage", "")
            status = r["status"]

            # Parse time
            try:
                dt = datetime.fromisoformat(r["scheduled_time"])
                time_str = dt.strftime("%I:%M %p")
            except Exception:
                time_str = r["scheduled_time"]

            with st.container():
                col1, col2, col3 = st.columns([4, 1, 1])
                with col1:
                    emoji = STATUS_EMOJI.get(status, "⏳")
                    color = STATUS_COLOR.get(status, "#888")
                    st.markdown(
                        f"{emoji} &nbsp; **{med_name}** `{dosage}`  \n"
                        f"<span style='color:#888;font-size:13px'>{time_str} &nbsp;·&nbsp; "
                        f"<span style='color:{color}'>{status.capitalize()}</span></span>",
                        unsafe_allow_html=True,
                    )
                if status == "pending":
                    with col2:
                        if st.button("✅ Taken", key=f"taken_{r['id']}", use_container_width=True):
                            confirm_reminder(r["id"], "taken")
                            st.rerun()
                    with col3:
                        if st.button("⏭ Skip", key=f"skip_{r['id']}", use_container_width=True):
                            confirm_reminder(r["id"], "skipped")
                            st.rerun()

        # Adherence mini-stats
        stats = get_adherence_stats(member["id"], days=7)
        if stats["total"] > 0:
            rate_color = "#5cb85c" if stats["rate"] >= 80 else "#f0ad4e" if stats["rate"] >= 50 else "#d9534f"
            st.markdown(
                f"<span style='font-size:12px;color:#888'>"
                f"Last 7 days: &nbsp;"
                f"<span style='color:{rate_color};font-weight:600'>{stats['rate']}% adherence</span>"
                f" &nbsp;·&nbsp; {stats['taken']} taken &nbsp;·&nbsp; {stats['missed']} missed"
                f"</span>",
                unsafe_allow_html=True,
            )
        st.markdown("")

    if not any_reminders:
        st.success("🎉 No reminders scheduled for today, or all done!")
        st.markdown(
            "<span style='color:#888;font-size:13px'>"
            "Add medications to start tracking doses."
            "</span>",
            unsafe_allow_html=True,
        )
        if st.button("💊 Add medications"):
            st.session_state.page = "medications"
            st.rerun()
