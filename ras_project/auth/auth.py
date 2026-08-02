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

    # Presence-only marker so CSS (.stApp:has(.auth-page)) can swap in the
    # gradient backdrop for the whole page — doesn't need to "contain"
    # anything itself.
    st.markdown('<div class="auth-page"></div>', unsafe_allow_html=True)

    # Real Streamlit container (not a raw unclosed <div>) so every widget
    # below is genuinely nested inside it in the DOM — CSS targets it via
    # the `.st-key-auth_card` class Streamlit gives keyed containers.
    with st.container(key="auth_card"):
        st.markdown('<div class="auth-orb o1"></div><div class="auth-orb o2"></div>',
                   unsafe_allow_html=True)
        st.markdown(
            '<div class="auth-brand">'
            '  <div class="auth-logo-badge">R</div>'
            '  <span class="auth-mark">RAS Document Intelligence</span>'
            '  <span class="auth-tagline">Ask anything. Backed by your own documents.</span>'
            '</div>'
            '<div class="auth-welcome">Welcome</div>'
            '<div class="auth-sub">Sign in to pick up where you left off</div>',
            unsafe_allow_html=True)

        tab_login, tab_signup, tab_forgot = st.tabs(["Log in", "Sign up", "Forgot password"])

        with tab_login:
            show_login_pw = st.checkbox("Show password", key="login_pw_show")
            with st.form("login_form"):
                username = st.text_input("Username", key="login_username", placeholder="Your username", icon=":material/person:")
                password = st.text_input("Password", type=("default" if show_login_pw else "password"),
                                         key="login_password", placeholder="Your password", icon=":material/lock:")
                submitted = st.form_submit_button("Log in", use_container_width=True, type="primary")
            if submitted:
                if not username.strip() or not password:
                    st.error("Enter both your username and password.")
                else:
                    try:
                        user = authenticate_user(username, password)
                    except AuthError as e:
                        st.error(str(e))
                    else:
                        _finish_login(user)

        with tab_signup:
            show_signup_pw = st.checkbox("Show password", key="signup_pw_show")
            with st.form("signup_form"):
                new_username = st.text_input("Choose a username", key="signup_username",
                                             placeholder="e.g. jane_doe", icon=":material/person:")
                pw_type = "default" if show_signup_pw else "password"
                new_password = st.text_input("Choose a password", type=pw_type, key="signup_password",
                                             placeholder="At least 8 characters", icon=":material/lock:")
                confirm      = st.text_input("Confirm password", type=pw_type, key="signup_confirm",
                                             placeholder="Re-enter your password", icon=":material/lock:")
                st.caption("Pick a security question — it's how you'll recover your account "
                          "if you forget your password. No email required.")
                question = st.selectbox("Security question", SECURITY_QUESTIONS, key="signup_question")
                answer   = st.text_input("Your answer", key="signup_answer", icon=":material/chat_bubble:")
                submitted2 = st.form_submit_button("Create account", use_container_width=True, type="primary")
            if submitted2:
                if not new_username.strip() or not new_password:
                    st.error("Choose a username and password first.")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters.")
                elif new_password != confirm:
                    st.error("Passwords don't match.")
                elif not answer.strip():
                    st.error("Add an answer to your security question — it's needed for password recovery.")
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

        st.markdown(
            '<div class="auth-note">Your documents stay private to your account</div>',
            unsafe_allow_html=True)
    st.stop()


def _render_forgot_password():
    st.caption("Answer your security question to set a new password. No email needed.")

    if "forgot_username" not in st.session_state:
        st.session_state.forgot_username = ""

    with st.form("forgot_lookup_form"):
        lookup_username = st.text_input("Your username", key="forgot_lookup_username",
                                        placeholder="Enter your username", icon=":material/person:")
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
        show_forgot_pw = st.checkbox("Show password", key="forgot_pw_show")
        pw_type = "default" if show_forgot_pw else "password"
        with st.form("forgot_reset_form"):
            answer   = st.text_input("Your answer", key="forgot_answer", icon=":material/chat_bubble:")
            new_pw   = st.text_input("New password", type=pw_type, key="forgot_new_pw", icon=":material/lock:")
            confirm  = st.text_input("Confirm new password", type=pw_type, key="forgot_confirm_pw", icon=":material/lock:")
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
    st.markdown('<div class="auth-page"></div>', unsafe_allow_html=True)
    with st.container(key="auth_card"):
        st.markdown('<div class="auth-orb o1"></div><div class="auth-orb o2"></div>',
                   unsafe_allow_html=True)
        st.markdown(
            '<div class="auth-brand"><div class="auth-logo-badge">R</div>'
            '<span class="auth-mark">Set a new password</span>'
            '<span class="auth-tagline">An admin reset your password — choose a new one to continue</span>'
            '</div>', unsafe_allow_html=True)
        show_forced_pw = st.checkbox("Show password", key="forced_pw_show")
        pw_type = "default" if show_forced_pw else "password"
        with st.form("forced_pw_change"):
            new_pw  = st.text_input("New password", type=pw_type, key="forced_new_pw", icon=":material/lock:")
            confirm = st.text_input("Confirm new password", type=pw_type, key="forced_confirm_pw", icon=":material/lock:")
            submitted = st.form_submit_button("Set new password", use_container_width=True, type="primary")
        if submitted:
            if new_pw != confirm:
                st.error("Passwords don't match.")
            elif len(new_pw) < 8:
                st.error("Password must be at least 8 characters.")
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
