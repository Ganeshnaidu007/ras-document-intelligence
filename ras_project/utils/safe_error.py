"""utils/safe_error.py — user-facing error display that never leaks internals.

Streamlit's default pattern of `st.error(f"...{e}")` puts raw exception
text (file paths, library internals, sometimes SQL or API responses) in
front of the user. In a multi-user app that's both an information leak
and confusing. This renders a short reference code the user can quote,
while the real exception + traceback goes to the server log only.
"""
import time
import streamlit as st
from utils.logger import get_logger

logger = get_logger(__name__)


def show_safe_error(user_message: str, exc: Exception = None, placeholder=None):
    """Show a generic message + reference code to the user. Logs full
    exception detail server-side via logger.exception (call this from
    inside an `except` block so the traceback is captured)."""
    ref = f"{int(time.time()) % 100000:05d}"
    if exc is not None:
        logger.exception(f"[ref={ref}] {user_message}")
    target = placeholder if placeholder is not None else st
    target.error(f"{user_message} (reference: {ref}). If this keeps happening, "
                 f"share that reference code with your admin.")
