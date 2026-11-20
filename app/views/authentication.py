"""Login and account registration screens."""

import streamlit as st

from app.auth import AuthenticationManager


def render_authentication_page(auth: AuthenticationManager) -> None:
    st.title("🏢 HR Analytics Portal")
    st.caption("Sign in to view workforce data, or create a read-only account.")

    login_tab, signup_tab = st.tabs(["Sign in", "Create account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
            if submitted:
                user = auth.login(email, password)
                if user:
                    st.session_state.current_user = user
                    st.rerun()
                else:
                    st.error("Email or password is incorrect.")

    with signup_tab:
        st.info("New accounts are read-only. HR access requires the administrator's HR signup code.")
        with st.form("signup_form"):
            full_name = st.text_input("Full name", key="signup_name")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input(
                "Password (at least 12 characters)",
                type="password",
                key="signup_password",
            )
            confirm_password = st.text_input(
                "Confirm password",
                type="password",
                key="signup_confirm_password",
            )
            hr_signup_code = st.text_input(
                "HR signup code (leave blank for read-only access)",
                type="password",
                key="signup_hr_code",
            )
            submitted = st.form_submit_button("Create account", use_container_width=True)
            if submitted:
                if password != confirm_password:
                    st.error("The passwords do not match.")
                else:
                    try:
                        user = auth.register(full_name, email, password, hr_signup_code)
                        st.session_state.current_user = user
                        st.rerun()
                    except ValueError as ex:
                        st.error(str(ex))
