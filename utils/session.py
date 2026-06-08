import streamlit as st


def init_session():
    if "user" not in st.session_state:
        st.session_state.user = None
    if "page" not in st.session_state:
        st.session_state.page = "login"


def is_logged_in() -> bool:
    return st.session_state.get("user") is not None


def get_user() -> dict | None:
    return st.session_state.get("user")


def login(user: dict):
    st.session_state.user = user


def logout():
    st.session_state.user = None
    st.session_state.page = "login"
    st.rerun()
