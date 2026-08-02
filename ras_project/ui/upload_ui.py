"""ui/upload_ui.py — Upload panels."""
import hashlib
import streamlit as st
from config.settings import SUPPORTED_SOURCE_TYPES, SUPPORTED_QUESTION_TYPES, MAX_FILE_SIZE_MB


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def _chip(f):
    sz   = getattr(f, "size", 0) / 1024
    szs  = f"{sz:.0f} KB" if sz < 1024 else f"{sz/1024:.1f} MB"
    ext  = f.name.rsplit(".",1)[-1].upper() if "." in f.name else "FILE"
    st.markdown(
        f'<span class="file-chip">'
        f'<span class="ftype">{ext}</span>'
        f'{f.name}'
        f'<span class="fsz">{szs}</span>'
        f'</span>',
        unsafe_allow_html=True,
    )


def render_source_upload():
    st.markdown('<span class="label">Source Documents</span>', unsafe_allow_html=True)
    st.markdown('<div class="helper-note">You can upload multiple PDFs, DOCX, or TXT files at once.</div>', unsafe_allow_html=True)

    remaining = None
    user_id = st.session_state.get("user_id")
    if user_id:
        from db.user_store import uploads_remaining_today
        remaining = uploads_remaining_today(user_id)
        st.caption(f"{remaining} file upload(s) left today")

    tab_file, tab_text = st.tabs(["Upload files", "Paste text"])
    with tab_file:
        uploaded = st.file_uploader(
            "source_files_uploader",
            type=SUPPORTED_SOURCE_TYPES,
            accept_multiple_files=True,
            key="source_uploader",
            help=f"PDF · DOCX · TXT  ·  Max {MAX_FILE_SIZE_MB} MB each",
            label_visibility="collapsed",
            disabled=(remaining == 0),
        )
        if uploaded:
            seen, unique, dupes = {}, [], []
            for f in uploaded:
                h = _hash(f.read()); f.seek(0)
                if h in seen: dupes.append(f.name)
                else: seen[h] = True; unique.append(f)
            if remaining is not None and len(unique) > remaining:
                st.error(f"That's {len(unique)} files but you only have {remaining} upload(s) "
                        f"left today — only the first {remaining} will be used.")
                unique = unique[:remaining]
            st.session_state.source_files = unique
            if dupes:
                st.caption(f"Duplicates skipped: {', '.join(dupes)}")
            for f in unique:
                _chip(f)
        elif st.session_state.get("source_files"):
            for f in st.session_state.source_files:
                if hasattr(f, "name"): _chip(f)

    with tab_text:
        txt = st.text_area("Paste content", height=160,
                           placeholder="Paste any document text here...",
                           label_visibility="collapsed", key="src_text_area")
        r1, r2 = st.columns([3,1])
        with r1:
            name = st.text_input("Document name", value="document",
                                 label_visibility="collapsed",
                                 placeholder="Name this document",
                                 key="src_text_name")
        with r2:
            if st.button("Add", key="add_src_txt", use_container_width=True):
                if txt.strip():
                    from io import BytesIO
                    n = f"{(name or 'document').strip()}.txt"
                    b = BytesIO(txt.encode()); b.name = n; b.size = len(txt.encode())
                    st.session_state.source_files = list(st.session_state.get("source_files", [])) + [b]
                    st.success(f"Added {n}")


def render_question_upload():
    st.markdown('<span class="label">Question Document</span>', unsafe_allow_html=True)
    st.markdown('<div class="helper-note">Upload a document with your questions, or type them directly.</div>', unsafe_allow_html=True)

    tab_file, tab_text = st.tabs(["Upload file", "Type questions"])
    with tab_file:
        uploaded = st.file_uploader(
            "question_file_uploader",
            type=SUPPORTED_QUESTION_TYPES,
            accept_multiple_files=False,
            key="question_uploader",
            label_visibility="collapsed",
        )
        if uploaded:
            st.session_state.question_file = uploaded
            _chip(uploaded)
        elif st.session_state.get("question_file") and hasattr(st.session_state.question_file,"name"):
            _chip(st.session_state.question_file)

    with tab_text:
        q = st.text_area("Type questions", height=150,
                         placeholder="1. What is the main finding?\n2. What methods were used?\n3. What are the limitations?",
                         label_visibility="collapsed", key="q_text_area")
        if st.button("Use these questions", key="use_q_text", use_container_width=True):
            if q.strip():
                from io import BytesIO
                b = BytesIO(q.encode()); b.name = "questions.txt"; b.size = len(q.encode())
                st.session_state.question_file = b
                n = len([l for l in q.splitlines() if l.strip()])
                st.success(f"{n} question{'s' if n!=1 else ''} ready")
            else:
                st.error("Enter at least one question.")