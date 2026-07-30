"""auth/auth.py — Real per-account login: username + password + a security
question set at signup (used only for self-service password recovery).

Call require_login() at the very top of the app. It renders the login/signup
form and calls st.stop() itself if the person isn't authenticated yet, so
nothing after it in the script runs until they're in.
"""
import streamlit as st
from db.user_store import (
    register_user, authenticate_user, reset_password, AuthError,
    SECURITY_QUESTIONS, get_security_question, reset_password_with_security_answer,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def require_login():
    if st.session_state.get("authed") and st.session_state.get("user_id"):
        if st.session_state.get("must_change_password"):
            _render_forced_password_change()
        return {
            "id": st.session_state.user_id,
            "username": st.session_state.user_key,
            "display_name": st.session_state.user_name,
        }

    st.markdown('<div class="auth-shell">', unsafe_allow_html=True)
    st.markdown('<div class="auth-brand"><span class="auth-mark">RAS</span>'
               '<span class="auth-tagline">Document Intelligence</span></div>',
               unsafe_allow_html=True)

    tab_login, tab_signup, tab_forgot = st.tabs(["Log in", "Sign up", "Forgot password"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log in", use_container_width=True, type="primary")
        if submitted:
            try:
                user = authenticate_user(username, password)
            except AuthError as e:
                st.error(str(e))
            else:
                _finish_login(user)

    with tab_signup:
        with st.form("signup_form"):
            new_username = st.text_input("Choose a username", key="signup_username")
            new_password = st.text_input("Choose a password", type="password", key="signup_password")
            confirm      = st.text_input("Confirm password", type="password", key="signup_confirm")
            st.caption("Pick a security question — it's how you'll recover your account "
                      "if you forget your password. No email required.")
            question = st.selectbox("Security question", SECURITY_QUESTIONS, key="signup_question")
            answer   = st.text_input("Your answer", key="signup_answer")
            submitted2 = st.form_submit_button("Create account", use_container_width=True, type="primary")
        if submitted2:
            if new_password != confirm:
                st.error("Passwords don't match.")
            else:
                try:
                    user = register_user(new_username, new_password, question, answer)
                except AuthError as e:
                    st.error(str(e))
                else:
                    st.success("Account created — logging you in...")
                    _finish_login(user)

    with tab_forgot:
        _render_forgot_password()

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


def _render_forgot_password():
    st.caption("Answer your security question to set a new password. No email needed.")

    if "forgot_username" not in st.session_state:
        st.session_state.forgot_username = ""

    with st.form("forgot_lookup_form"):
        lookup_username = st.text_input("Your username", key="forgot_lookup_username")
        lookup_submitted = st.form_submit_button("Continue", use_container_width=True)
    if lookup_submitted:
        question = get_security_question(lookup_username)
        if not question:
            # Same message whether the username exists or not — doesn't
            # reveal which usernames are registered.
            st.error("Couldn't find that account, or it has no security question set.")
        else:
            st.session_state.forgot_username = lookup_username
            st.session_state.forgot_question = question

    if st.session_state.get("forgot_question"):
        st.info(f"**{st.session_state.forgot_question}**")
        with st.form("forgot_reset_form"):
            answer   = st.text_input("Your answer", key="forgot_answer")
            new_pw   = st.text_input("New password", type="password", key="forgot_new_pw")
            confirm  = st.text_input("Confirm new password", type="password", key="forgot_confirm_pw")
            reset_submitted = st.form_submit_button("Reset password", use_container_width=True, type="primary")
        if reset_submitted:
            if new_pw != confirm:
                st.error("Passwords don't match.")
            else:
                try:
                    reset_password_with_security_answer(
                        st.session_state.forgot_username, answer, new_pw)
                    st.session_state.pop("forgot_question", None)
                    st.success("Password reset — you can log in with it now.")
                except AuthError as e:
                    st.error(str(e))


def _finish_login(user):
    st.session_state.authed         = True
    st.session_state.user_id        = user["id"]
    st.session_state.user_key       = user["username"]
    st.session_state.user_name      = user["display_name"]
    st.session_state.just_logged_in = True
    st.session_state.must_change_password = user.get("must_change_password", False)
    logger.info(f"Login: {user['display_name']} (id={user['id']})")
    st.rerun()


def _render_forced_password_change():
    """Shown instead of the app when an admin has reset this user's password
    — they must set a new one before doing anything else."""
    st.markdown("## Set a new password")
    st.info("An admin reset your password. Choose a new one to continue.")
    with st.form("forced_pw_change"):
        new_pw  = st.text_input("New password", type="password", key="forced_new_pw")
        confirm = st.text_input("Confirm new password", type="password", key="forced_confirm_pw")
        submitted = st.form_submit_button("Set new password", use_container_width=True, type="primary")
    if submitted:
        if new_pw != confirm:
            st.error("Passwords don't match.")
        else:
            try:
                reset_password(st.session_state.user_id, new_pw, force_change=False)
                st.session_state.must_change_password = False
                st.success("Password updated.")
                st.rerun()
            except AuthError as e:
                st.error(str(e))
    st.stop()


def logout():
    keep_nothing = ("authed", "user_id", "user_key", "user_name", "indexes_built",
                    "retriever", "reranker_obj", "embedder", "chat_history",
                    "chat_agent", "chat_conv_memory", "chat_session_id", "chat_doc_ids",
                    "show_admin", "admin_authed", "must_change_password")
    for k in keep_nothing:
        st.session_state.pop(k, None)
    st.rerun()


def is_admin() -> bool:
    return bool(st.session_state.get("admin_authed"))
