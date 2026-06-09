import streamlit as st
from utils.session import init_session, is_logged_in, get_user, logout
from utils.db import login_user, create_user
from utils.email import send_welcome_email
import pages.dashboard as dashboard
import pages.medications as medications
import pages.family as family
from scheduler.worker import start_scheduler


st.set_page_config(
    page_title="MedAlly",
    page_icon="💊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Global styles ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .block-container { padding-top: 2rem; }
  .stButton > button { border-radius: 8px; }
  div[data-testid="stSidebarNav"] { display: none; }
</style>
""", unsafe_allow_html=True)

init_session()
start_scheduler()

start_scheduler()
# Seed today's reminders on every app startup
from utils.db import generate_todays_reminders
generate_todays_reminders()


# ── Sidebar nav (only when logged in) ────────────────────────────────────────
def render_sidebar():
    user = get_user()
    with st.sidebar:
        st.markdown(f"### 👋 {user['name']}")
        st.markdown("---")
        if st.button("🏠  Dashboard", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
        if st.button("👨‍👩‍👧  Family", use_container_width=True):
            st.session_state.page = "family"
            st.rerun()
        if st.button("💊  Medications", use_container_width=True):
            st.session_state.page = "medications"
            st.rerun()
        st.markdown("---")
        if st.button("🚪  Sign out", use_container_width=True):
            logout()


# ── Auth pages ────────────────────────────────────────────────────────────────
def render_login():
    st.markdown("## 💊 MedAlly")
    st.markdown("*Family medication management, simplified.*")
    st.markdown("---")

    tab_login, tab_signup = st.tabs(["Sign in", "Create account"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
        if submitted:
            if not email or not password:
                st.error("Please fill in all fields")
            else:
                user = login_user(email.strip().lower(), password)
                if user:
                    from utils.session import login
                    login(user)
                    st.session_state.page = "dashboard"
                    st.rerun()
                else:
                    st.error("Invalid email or password")

    with tab_signup:
        with st.form("signup_form"):
            name = st.text_input("Your name")
            email = st.text_input("Email", key="su_email")
            password = st.text_input("Password", type="password", key="su_pw")
            password2 = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create account", use_container_width=True)
        if submitted:
            if not all([name, email, password, password2]):
                st.error("Please fill in all fields")
            elif password != password2:
                st.error("Passwords don't match")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                user = create_user(email.strip().lower(), password, name.strip())
                if user:
                    send_welcome_email(user["email"], user["name"])
                    from utils.session import login
                    login(user)
                    st.session_state.page = "family"
                    st.success("Account created! Let's add your family.")
                    st.rerun()
                else:
                    st.error(f"create_user returned None — check terminal for errors")


# ── Router ────────────────────────────────────────────────────────────────────
if not is_logged_in():
    render_login()
else:
    render_sidebar()
    page = st.session_state.get("page", "dashboard")
    if page == "dashboard":
        dashboard.render()
    elif page == "family":
        family.render()
    elif page == "medications":
        medications.render()
    else:
        dashboard.render()
