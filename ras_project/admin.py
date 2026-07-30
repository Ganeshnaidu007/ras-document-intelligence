"""admin.py — standalone admin dashboard.

Deliberately a SEPARATE Streamlit app from app.py. There is no link,
button, or route inside the main app that leads here — the only way in
is knowing this file exists and running it yourself:

    streamlit run admin.py --server.port 8502

Run it on a different port than the main app (and, in production, put
it behind its own auth/network restriction — see the note at the
bottom of this file) so regular users never even know the URL exists.
It's still code-gated by RAS_ADMIN_CODE on top of that.
"""
import os
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import utils.model_cache  # noqa: F401 — sets KMP_DUPLICATE_LIB_OK etc. before any model import
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")

import streamlit as st

st.set_page_config(
    page_title="RAS — Admin",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from config.settings import ADMIN_CODE
from ui.admin_ui import render_admin_page

if ADMIN_CODE == "admin-changeme":
    st.error(
        "**Admin dashboard is disabled.** `RAS_ADMIN_CODE` is still set to the "
        "default value (`admin-changeme`). Set real credentials before running this:\n\n"
        "- Locally: add `RAS_ADMIN_USERNAME = \"your-username\"` and "
        "`RAS_ADMIN_CODE = \"your-password\"` to `.streamlit/secrets.toml`\n"
        "- Or set the `RAS_ADMIN_USERNAME` / `RAS_ADMIN_CODE` environment variables\n\n"
        "This check exists so the admin dashboard can never accidentally ship "
        "reachable with a publicly-known password. (Username defaults to `admin` "
        "if you don't set one — only the password needs to be changed to unlock this page.)"
    )
    st.stop()

render_admin_page()

# ── Production hardening note ──────────────────────────────────────────────
# Running two `streamlit run` processes (app.py on one port, admin.py on
# another) means:
#   - Regular users hitting the main app URL can NEVER reach this page —
#     it isn't imported, linked, or routed to from app.py at all.
#   - On Streamlit Community Cloud you'd deploy this as a second app
#     pointing at admin.py, with its own (ideally different, harder)
#     app URL that you don't share publicly.
#   - For real production use, put this behind an extra layer your
#     platform provides — e.g. IP allowlisting, a reverse-proxy basic-auth
#     rule, or Cloud Run/behind-VPN — so the admin code isn't the only
#     thing standing between the public internet and this page.
