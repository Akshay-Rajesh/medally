import streamlit as st
from utils.session import get_user
from utils.db import get_family_members, create_family_member, delete_family_member

RELATIONSHIPS = ["self", "father", "mother", "spouse", "child", "sibling", "other"]
GENDERS = ["", "Male", "Female", "Prefer not to say"]


def render():
    user = get_user()
    st.markdown("## 👨‍👩‍👧 Family members")

    members = get_family_members(user["id"])

    # ── Existing members ──────────────────────────────────────────────────────
    if members:
        for m in members:
            col1, col2 = st.columns([5, 1])
            with col1:
                rel_label = m["relationship"].capitalize()
                age_label = f", age {m['age']}" if m.get("age") else ""
                st.markdown(
                    f"**{m['name']}** &nbsp;·&nbsp; "
                    f"<span style='color:#888;font-size:13px'>{rel_label}{age_label}</span>",
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("🗑", key=f"del_{m['id']}", help="Remove"):
                    delete_family_member(m["id"])
                    st.rerun()
        st.markdown("---")
    else:
        st.info("No family members yet. Add someone below to get started.")

    # ── Add new member ────────────────────────────────────────────────────────
    st.markdown("#### Add a family member")
    with st.form("add_member_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name *")
            relationship = st.selectbox("Relationship *", RELATIONSHIPS)
        with col2:
            age = st.number_input("Age", min_value=0, max_value=120, value=0)
            gender = st.selectbox("Gender", GENDERS)

        submitted = st.form_submit_button("Add member", use_container_width=True)

    if submitted:
        if not name.strip():
            st.error("Name is required")
        else:
            member = create_family_member(
                user_id=user["id"],
                name=name.strip(),
                relationship=relationship,
                age=int(age) if age > 0 else None,
                gender=gender if gender else None,
            )
            if member:
                st.success(f"Added {name}!")
                st.rerun()
            else:
                st.error("Something went wrong. Please try again.")
