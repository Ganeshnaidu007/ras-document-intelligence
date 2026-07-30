"""ui/admin_ui.py — Admin dashboard: users, storage, live memory state, audit log.

Gated by its own separate code (config.settings.ADMIN_CODE) — a normal user
account can never reach it just by logging in.
"""
import os, time, hmac
import streamlit as st
from config.settings import ADMIN_USERNAME, ADMIN_CODE, USER_DB_PATH, MAX_HOT_USERS, MAX_UPLOADS_PER_DAY
from db import user_store, session_cache
from utils.logger import get_logger

logger = get_logger(__name__)


def _ago(ts: float) -> str:
    if not ts: return "—"
    s = time.time() - ts
    if s < 60: return "just now"
    if s < 3600: return f"{int(s//60)}m ago"
    if s < 86400: return f"{int(s//3600)}h ago"
    return f"{int(s//86400)}d ago"


def render_admin_page():
    st.markdown("## 🛠️ Admin Dashboard")

    if not st.session_state.get("admin_authed"):
        st.markdown('<div style="max-width:360px;margin:2rem auto 0">', unsafe_allow_html=True)
        with st.form("admin_login"):
            username = st.text_input("Admin username")
            password = st.text_input("Admin password", type="password")
            ok = st.form_submit_button("Log in", use_container_width=True, type="primary")
        st.markdown('</div>', unsafe_allow_html=True)
        if ok:
            # Constant-time comparison on both fields — a plain `==` on
            # strings short-circuits at the first mismatched character,
            # which leaks (very slightly) how many characters were guessed
            # correctly over enough attempts. hmac.compare_digest always
            # takes the same time regardless of where the mismatch is.
            user_ok = hmac.compare_digest(username, ADMIN_USERNAME)
            pass_ok = hmac.compare_digest(password, ADMIN_CODE)
            if user_ok and pass_ok:
                st.session_state.admin_authed = True
                st.rerun()
            else:
                st.error("Incorrect username or password.")
        return

    users = user_store.list_all_users()
    hot_keys = session_cache.hot_keys()
    disk_mb = user_store.disk_usage_mb()
    db_mb = round(os.path.getsize(USER_DB_PATH) / 1024 / 1024, 2) if os.path.exists(USER_DB_PATH) else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total users", len(users))
    c2.metric("Hot chats in RAM now", f"{len(hot_keys)} / {MAX_HOT_USERS}")
    c3.metric("Saved documents on disk", f"{disk_mb} MB")
    c4.metric("Database file size", f"{db_mb} MB")

    # ── Upload-cap alerts ─────────────────────────────────────────────────
    capped = user_store.users_who_hit_cap_recently()
    if capped:
        st.divider()
        st.markdown("### ⚠️ Hitting their upload cap repeatedly")
        st.caption("These users have hit the daily upload limit 2+ times in the last 24h — "
                  "consider raising their cap or checking in with them.")
        for u in capped:
            st.caption(f"**{u['display_name']}** (@{u['username']}) — hit the cap {u['hits']} time(s)")

    st.divider()
    st.markdown("### Users")
    st.caption(f"Upload cap: {MAX_UPLOADS_PER_DAY} files / 24h per user")
    if not users:
        st.caption("No users yet.")
    for u in users:
        with st.container(border=True):
            # Wider action-button columns than before — "Reset password" /
            # "Delete all data" were getting clipped/wrapped at 1.3 units
            # wide. Info columns get a bit less room in exchange.
            cols = st.columns([2.6, 1.8, 1.6, 2, 1.6, 1.6, 1.8])
            cols[0].markdown(f"**{u['display_name']}**  \n`@{u['username']}`")
            today = user_store.documents_uploaded_today(u["id"])
            cols[1].caption(f"Docs: {u['num_docs']}  ({today}/{MAX_UPLOADS_PER_DAY} today)")
            cols[2].caption(f"Chunks: {u['num_chunks']}")
            cols[3].caption(f"Chats: {u['num_sessions']} · Q&A: {u['num_qa']}")
            cols[4].caption(f"Active: {_ago(u['last_active'])}")

            if cols[5].button("Reset password", key=f"resetpw_{u['id']}", use_container_width=True):
                temp_pw = user_store.admin_reset_password(u["id"])
                st.session_state[f"_temp_pw_{u['id']}"] = temp_pw

            confirm_key = f"_confirm_del_user_{u['id']}"
            if not st.session_state.get(confirm_key):
                if cols[6].button("Delete all data", key=f"del_{u['id']}", use_container_width=True):
                    st.session_state[confirm_key] = True
                    st.rerun()
            else:
                if cols[6].button("Confirm delete", key=f"del_confirm_{u['id']}",
                                  use_container_width=True, type="primary"):
                    user_store.delete_user_completely(u["id"])
                    session_cache.drop_prefix("docs:")  # conservative: clear any of their cached chats
                    user_store.log_admin_action("delete_user", target=u["username"])
                    st.session_state.pop(confirm_key, None)
                    st.success(f"Deleted all data for {u['display_name']} (@{u['username']}).")
                    st.rerun()

            if st.session_state.get(confirm_key):
                cc1, cc2 = st.columns([5, 1.6])
                cc1.warning(f"This permanently deletes every document, chat, and Q&A for "
                           f"**{u['display_name']}**. This can't be undone.")
                if cc2.button("Cancel", key=f"del_cancel_{u['id']}", use_container_width=True):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()

            temp_pw = st.session_state.pop(f"_temp_pw_{u['id']}", None)
            if temp_pw:
                st.success(f"Temporary password for {u['display_name']}: `{temp_pw}`  \n"
                          f"Send this to them securely — it's shown once and forces a "
                          f"password change on their next login.")

    # ── Usage dashboard ───────────────────────────────────────────────────
    st.divider()
    st.markdown("### Usage")
    qpd = user_store.questions_per_day(days=30)
    if qpd:
        st.caption("Questions asked per day (last 30 days)")
        st.bar_chart({row["day"]: row["count"] for row in qpd})
    else:
        st.caption("No questions asked yet.")

    col_docs, col_active = st.columns(2)
    with col_docs:
        st.markdown("**Most-uploaded documents**")
        top_docs = user_store.top_documents()
        if top_docs:
            for d in top_docs:
                st.caption(f"{d['filename']} — {d['uploads']} upload(s), {d['total_chunks']} chunks")
        else:
            st.caption("No documents yet.")
    with col_active:
        st.markdown("**Most active users**")
        active = user_store.most_active_users()
        if active:
            for a in active:
                st.caption(f"{a['display_name']} (@{a['username']}) — {a['num_questions']} question(s)")
        else:
            st.caption("No questions asked yet.")

    st.divider()
    st.markdown("### Admin activity log")
    log = user_store.get_audit_log(limit=20)
    if not log:
        st.caption("No admin actions logged yet.")
    for entry in log:
        st.caption(f"[{_ago(entry['timestamp'])}] **{entry['actor']}** → "
                  f"{entry['action']} · `{entry['target']}`")

    st.divider()
    st.markdown("### Answer feedback")
    st.caption("There's no separate Good/Poor button anymore — clicking 🔄 Regenerate on an "
              "answer IS the negative signal (logged automatically). Every answer that's never "
              "regenerated is logged as implicitly good, so these numbers cover 100% of answers, "
              "not just the ones someone bothered to rate.")
    try:
        from utils.feedback_store import get_feedback_stats, get_recent_feedback
        stats = get_feedback_stats()
        fc1, fc2, fc3, fc4 = st.columns(4)
        fc1.metric("Total ratings", stats["total"])
        fc2.metric("Good", stats["thumbs_up"])
        fc3.metric("Poor (regenerated)", stats["thumbs_down"])
        fc4.metric("Satisfaction", f"{stats['satisfaction_pct']}%")
        recent = get_recent_feedback(limit=15)
        if recent:
            with st.expander("Recent ratings", expanded=False):
                for r in recent:
                    tag = "✅ Good" if r["rating"] == 1 else "⚠️ Regenerated"
                    st.caption(f"[{_ago(r['timestamp'])}] **{tag}** ({r.get('provider','')}) — "
                              f"\"{r['question'][:80]}\"  \n{r['answer'][:160]}…")
        else:
            st.caption("No ratings logged yet.")
    except Exception as e:
        st.caption(f"Feedback data unavailable: {e}")

    st.divider()
    if st.button("Log out of admin"):
        st.session_state.admin_authed = False
        st.rerun()
