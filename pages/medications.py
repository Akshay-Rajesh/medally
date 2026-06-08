import streamlit as st
from datetime import date, time
from utils.session import get_user
from utils.db import (
    get_family_members,
    get_medications,
    create_medication,
    deactivate_medication,
)

FREQUENCIES = {
    "Once daily": ["08:00"],
    "Twice daily": ["08:00", "20:00"],
    "Three times daily": ["08:00", "14:00", "20:00"],
    "Custom": [],
}


def render():
    user = get_user()
    st.markdown("## 💊 Medications")

    members = get_family_members(user["id"])
    if not members:
        st.warning("Add a family member first before adding medications.")
        if st.button("Go to Family →"):
            st.session_state.page = "family"
            st.rerun()
        return

    member_names = {m["id"]: m["name"] for m in members}

    # ── Member selector tabs ──────────────────────────────────────────────────
    selected_name = st.selectbox(
        "View medications for",
        options=list(member_names.values()),
    )
    selected_id = next(k for k, v in member_names.items() if v == selected_name)

    # ── Current medications ───────────────────────────────────────────────────
    meds = get_medications(selected_id)
    if meds:
        for med in meds:
            times_str = " · ".join(med.get("times_of_day", []))
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(
                    f"**{med['name']}** &nbsp; `{med['dosage']}`  \n"
                    f"<span style='color:#888;font-size:13px'>"
                    f"{med['frequency'].replace('_', ' ').title()} &nbsp;·&nbsp; {times_str}"
                    f"</span>",
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("🗑", key=f"del_med_{med['id']}", help="Remove"):
                    deactivate_medication(med["id"])
                    st.rerun()
        st.markdown("---")
    else:
        st.info(f"No medications added for {selected_name} yet.")

    # ── Add medication form ───────────────────────────────────────────────────
    st.markdown(f"#### Add medication for {selected_name}")

    with st.form("add_med_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            med_name = st.text_input("Medication name *", placeholder="e.g. Metformin")
            dosage = st.text_input("Dosage *", placeholder="e.g. 500mg")
        with col2:
            freq_label = st.selectbox("Frequency *", list(FREQUENCIES.keys()))
            start_date = st.date_input("Start date *", value=date.today())

        end_date = st.date_input(
            "End date (optional — leave blank for ongoing)",
            value=None,
        )

        # Custom time inputs
        custom_times = []
        if freq_label == "Custom":
            st.markdown("**Set reminder times**")
            n_times = st.number_input("Number of daily doses", min_value=1, max_value=6, value=1)
            for i in range(int(n_times)):
                t = st.time_input(f"Dose {i+1} time", value=time(8 + i*4, 0), key=f"ct_{i}")
                custom_times.append(t.strftime("%H:%M"))

        submitted = st.form_submit_button("Add medication", use_container_width=True)

    if submitted:
        if not med_name.strip() or not dosage.strip():
            st.error("Medication name and dosage are required")
        else:
            times = custom_times if freq_label == "Custom" else FREQUENCIES[freq_label]
            freq_key = freq_label.lower().replace(" ", "_")
            med = create_medication(
                family_member_id=selected_id,
                name=med_name.strip(),
                dosage=dosage.strip(),
                frequency=freq_key,
                times_of_day=times,
                start_date=start_date,
                end_date=end_date if end_date != date.today() else None,
            )
            if med:
                st.success(f"Added {med_name} for {selected_name}!")
                st.rerun()
            else:
                st.error("Something went wrong. Please try again.")
