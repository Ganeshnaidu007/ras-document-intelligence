"""ui/chat_ui.py — Chat mode: multiple chat threads and a persistent
document library per user, and per-chat document selection. Rendered as a
real st.sidebar, ChatGPT/Claude-style: new chat + chat list + files.

An earlier attempt moved this out of st.sidebar because it looked broken —
turned out the real causes were a CSS rule that let the page header overlap
and swallow clicks, and unrelated to the sidebar itself. Both are fixed now,
so a real left sidebar is back, since that's what actually gives this the
familiar chat-app layout.

Each "New chat" is its own thread with its own history and its own chosen
subset of previously-uploaded documents — nothing is auto-merged across
chats. Documents are processed once and reused across any number of chats.
"""
import os, hashlib
import streamlit as st
try:
    from streamlit_extras.stylable_container import stylable_container
    _HAS_EXTRAS = True
except ImportError:
    _HAS_EXTRAS = False
from utils.logger import get_logger
logger = get_logger(__name__)


# ── Document library: process one new upload, add it to the user's library ──
def _process_single_upload(uploaded_file, user_id, ocr_enabled, ocr_engine,
                           chunking_method, chunk_size, chunk_overlap, embedding_model):
    """Pure function — every setting it needs is passed in as a plain
    argument, not read from st.session_state. That's deliberate: this runs
    inside a ThreadPoolExecutor worker thread when uploading multiple files
    at once, and st.session_state has no ScriptRunContext on any thread but
    the main one — reading it there raises, not just warns. All session_state
    reads happen once, up front, on the main thread, in the caller below."""
    from ingestion.pdf_parser   import PDFParser
    from ingestion.docx_parser  import DOCXParser
    from ingestion.text_cleaner import TextCleaner
    from chunking.chunk_manager import ChunkManager
    from embeddings.embedding_factory import EmbeddingFactory
    from utils.helpers import save_uploaded_file
    from db.user_store import save_document

    path = save_uploaded_file(uploaded_file, "sources", user_id=user_id)
    ext  = os.path.splitext(path)[1].lower()
    pdf_p   = PDFParser(ocr_enabled=ocr_enabled, ocr_engine=ocr_engine)
    docx_p  = DOCXParser()
    cleaner = TextCleaner()

    if ext == ".pdf":
        doc = pdf_p.parse(path)
    elif ext in (".docx", ".doc"):
        doc = docx_p.parse(path)
    else:
        doc = {"source": path, "metadata": {},
               "pages": [{"page_number": 1,
                          "text": open(path, encoding="utf-8", errors="ignore").read(),
                          "tables": [], "source": os.path.basename(path)}]}
    doc["pages"] = [cleaner.clean(p) for p in doc["pages"]]

    cm = ChunkManager(method=chunking_method, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = cm.chunk_document(doc)
    if not chunks:
        return None
    embedder = EmbeddingFactory(embedding_model).get_embedder()
    vecs = embedder.embed_batch([c["text"] for c in chunks])
    for c, v in zip(chunks, vecs):
        c["embedding"] = v

    with open(path, "rb") as f:
        fhash = hashlib.sha256(f.read()).hexdigest()[:16]

    return save_document(
        user_id, uploaded_file.name, chunks, fhash,
        chunking_method, chunk_size, chunk_overlap, embedding_model,
        source_file_path=path), len(chunks)


def apply_doc_selection(user_id, session_id, doc_ids):
    from db import user_store, session_cache
    user_store.update_session_docs(session_id, doc_ids)
    if not doc_ids:
        st.session_state.retriever = None
        st.session_state.chat_doc_ids = []
        return
    chunks = user_store.load_documents_chunks(doc_ids)
    key = session_cache.doc_ids_key(doc_ids)
    bundle = session_cache.get_or_rebuild(
        key, chunks, st.session_state.embedding_model, st.session_state.retrieval_strategy,
        st.session_state.reranking_enabled, st.session_state.reranking_model)
    st.session_state.retriever    = bundle["retriever"]
    st.session_state.reranker_obj = bundle["reranker"]
    st.session_state.embedder     = bundle["embedder"]
    st.session_state.chat_doc_ids = doc_ids
    st.session_state.chat_agent   = None  # force agent rebuild against new retriever


def _load_session_into_view(user_id, session_id):
    from db import user_store
    s = user_store.get_chat_session(session_id)
    if not s:
        return
    st.session_state.chat_session_id = session_id
    st.session_state.chat_agent      = None
    if "chat_conv_memory" in st.session_state:
        st.session_state.chat_conv_memory.clear()

    history = user_store.get_session_history(session_id)
    chat_history = []
    for turn in history:
        ts = _format_ts(turn.get("timestamp"))
        chat_history.append({"role": "user", "content": turn["question"], "_ts": ts})
        chat_history.append({"role": "assistant", "content": turn["answer"],
                             "trace": [], "sources": [], "_question": turn["question"], "_ts": ts})
    st.session_state.chat_history = chat_history

    if s["doc_ids"]:
        apply_doc_selection(user_id, session_id, s["doc_ids"])
    else:
        st.session_state.retriever = None
        st.session_state.chat_doc_ids = []


def _render_sidebar(user_id):
    from db import user_store

    with st.sidebar:
        current_id = st.session_state.get("chat_session_id")
        user_store.prune_empty_sessions(user_id, keep_session_id=current_id)

        if st.button("New chat", icon=":material/add:", use_container_width=True, key="new_chat_btn", type="primary"):
            # Never create a second blank chat: if the chat that's already
            # open has no messages in it yet, clicking "New chat" again is a
            # no-op on the session itself — just reset the live view (in
            # case anything got left over) rather than inserting another
            # empty row. Document selection carries over from whatever chat
            # was open — uploaded documents live in the user's library
            # independent of any chat and are never touched here.
            carried_doc_ids = list(st.session_state.get("chat_doc_ids", []))
            if current_id and user_store.session_is_empty(current_id):
                new_id = current_id
            else:
                new_id = user_store.create_chat_session(user_id)
                if carried_doc_ids:
                    apply_doc_selection(user_id, new_id, carried_doc_ids)
            _load_session_into_view(user_id, new_id)
            st.rerun()

        st.markdown('<div class="sidebar-section-label">Recent Chats</div>', unsafe_allow_html=True)
        sessions = user_store.list_chat_sessions(user_id)
        if not sessions:
            st.caption("No chats yet.")
        for s in sessions:
            active = s["id"] == st.session_state.get("chat_session_id")
            label = s["title"] or "New chat"
            c_sel, c_del = st.columns([5, 1])
            with c_sel:
                if st.button(label, key=f"sess_{s['id']}", use_container_width=True,
                            type="primary" if active else "secondary"):
                    _load_session_into_view(user_id, s["id"])
                    st.rerun()
            with c_del:
                if st.button("", key=f"sess_del_{s['id']}", icon=":material/delete:",
                             help="Delete this chat", use_container_width=True):
                    st.session_state[f"_confirm_del_sess_{s['id']}"] = True

            if st.session_state.get(f"_confirm_del_sess_{s['id']}"):
                st.warning(f"Delete **{label}**? This only removes the chat "
                           f"conversation — your uploaded documents stay in your library.")
                c_yes, c_no = st.columns(2)
                if c_yes.button("Yes, delete", key=f"sess_del_yes_{s['id']}", use_container_width=True):
                    was_active = active
                    user_store.delete_session(s["id"])
                    st.session_state.pop(f"_confirm_del_sess_{s['id']}", None)
                    if was_active:
                        # The chat just open was the one deleted — start a
                        # fresh one so the view never points at a dead session.
                        remaining_docs = list(st.session_state.get("chat_doc_ids", []))
                        new_id = user_store.create_chat_session(user_id)
                        if remaining_docs:
                            apply_doc_selection(user_id, new_id, remaining_docs)
                        _load_session_into_view(user_id, new_id)
                    st.rerun()
                if c_no.button("Cancel", key=f"sess_del_no_{s['id']}", use_container_width=True):
                    st.session_state.pop(f"_confirm_del_sess_{s['id']}", None)
                    st.rerun()

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section-label">My Documents</div>', unsafe_allow_html=True)

        from db.user_store import uploads_remaining_today, UploadLimitExceeded
        remaining = uploads_remaining_today(user_id)
        st.caption(f"{remaining} upload(s) left today")
        st.markdown('<div class="helper-note">You can upload multiple PDFs, DOCX, or TXT files at once. '
                    'Supported: PDF, DOCX, TXT.</div>',
                    unsafe_allow_html=True)

        uploaded = st.file_uploader("Add files", key="chat_lib_uploader",
                                    accept_multiple_files=True, label_visibility="collapsed",
                                    disabled=(remaining <= 0))
        if uploaded and st.button("Process & add", icon=":material/upload:", use_container_width=True,
                                  key="lib_process_btn", disabled=(remaining <= 0)):
            if len(uploaded) > remaining:
                st.error(f"{len(uploaded)} files but only {remaining} left today.")
            else:
                import concurrent.futures
                # Read every setting the worker needs HERE, on the main
                # thread — st.session_state has no ScriptRunContext
                # inside a ThreadPoolExecutor worker, so it must not be
                # touched from within _process_single_upload itself.
                cfg = dict(
                    user_id=user_id,
                    ocr_enabled=st.session_state.get("ocr_enabled", False),
                    ocr_engine=st.session_state.get("ocr_engine", "tesseract"),
                    chunking_method=st.session_state.get("chunking_method", "Fixed"),
                    chunk_size=st.session_state.get("chunk_size", 500),
                    chunk_overlap=st.session_state.get("chunk_overlap", 50),
                    embedding_model=st.session_state.get("embedding_model", "all-MiniLM-L6-v2"),
                )
                import time
                t0 = time.time()
                with st.status(f"Processing {len(uploaded)} file(s)...", expanded=True) as status:
                    status.write("Uploading files...")
                    errors, new_doc_ids, total_chunks = [], [], 0
                    status.write("Extracting text (OCR where needed), chunking, and embedding...")
                    # Parallel, not one-at-a-time: parsing + chunking + embedding
                    # for each file is independent work, so N files no longer
                    # takes N times as long — capped at 4 concurrent so it
                    # doesn't overwhelm memory on smaller VPS instances.
                    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                        futures = {ex.submit(_process_single_upload, f, **cfg): f for f in uploaded}
                        for fut in concurrent.futures.as_completed(futures):
                            f = futures[fut]
                            try:
                                result = fut.result()
                                if result:
                                    doc_id, n_chunks = result
                                    new_doc_ids.append(doc_id)
                                    total_chunks += n_chunks
                            except UploadLimitExceeded as e:
                                errors.append(str(e))
                            except Exception:
                                logger.exception(f"Failed to process {f.name}")
                                errors.append(f"{f.name}: couldn't be processed.")
                    status.write("Indexing into your knowledge base...")
                    elapsed = time.time() - t0
                    status.update(label="Processing complete", state="complete", expanded=False)
                if errors:
                    st.error(errors[0])
                if new_doc_ids:
                    st.session_state["_last_build_status"] = {
                        "files": len(new_doc_ids), "chunks": total_chunks,
                        "model": cfg["embedding_model"], "elapsed": elapsed,
                    }
                if new_doc_ids:
                    # Belongs to THIS chat right away — no separate "select
                    # + apply" step needed before it can be used to answer
                    # questions here.
                    session_id = st.session_state.get("chat_session_id")
                    combined = list(dict.fromkeys(
                        list(st.session_state.get("chat_doc_ids", [])) + new_doc_ids))
                    apply_doc_selection(user_id, session_id, combined)
                    # Auto-workflow: uploaded doc(s) are already selected + active
                    # (apply_doc_selection above) and this sidebar only ever
                    # renders inside Chat Mode, so there's no extra "select /
                    # switch page" step for the user — just surface the ready
                    # state and let them type straight into the chat input.
                    st.toast("Your documents are ready. Ask anything.", icon=":material/check_circle:")
                    st.session_state["_docs_just_readied"] = True
                st.rerun()

        docs = user_store.list_user_documents(user_id)
        if docs:
            st.markdown('<div class="sidebar-section-label" style="margin-top:.9rem">Uploaded Files</div>',
                        unsafe_allow_html=True)
        if not docs:
            st.markdown(
                '<div class="empty-state-cta-wrap" style="padding:2rem 0.5rem">'
                '<div class="empty-illustration">'
                '<svg width="32" height="32" viewBox="0 0 24 24" fill="none">'
                '<path d="M6 2h9l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" fill="white"/>'
                '<path d="M15 2v5h5" fill="white" opacity=".6"/></svg></div>'
                '<div class="empty-state-title">No documents uploaded yet</div>'
                '<div class="empty-state-sub">Upload a document above to begin chatting.</div>'
                '</div>', unsafe_allow_html=True)
        else:
            current_ids = set(st.session_state.get("chat_doc_ids", []))
            picked = []
            for d in docs:
                is_selected = d["id"] in current_ids
                ext = (d["filename"].rsplit(".", 1)[-1].upper() if "." in d["filename"] else "FILE")[:4]

                border_css = ("border:1px solid var(--accent)!important;"
                              "box-shadow:0 0 0 1px var(--accent),0 4px 14px rgba(99,102,241,.18)!important;"
                              if is_selected else "border:1px solid var(--border)!important;")
                if _HAS_EXTRAS:
                    card_ctx = stylable_container(
                        key=f"doccard_{d['id']}",
                        css_styles=f"""
                        {{
                            {border_css}
                            background: var(--card);
                            border-radius: 12px;
                            padding: .6rem .8rem .3rem;
                            margin-bottom: .5rem;
                        }}
                        """)
                else:
                    card_ctx = st.container(border=True)

                with card_ctx:
                    selected_tag = ' · <span style="color:var(--accent2)">Selected</span>' if is_selected else ""
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:.6rem;margin-bottom:.3rem">'
                        f'<div class="doc-icon">{ext}</div>'
                        f'<div class="doc-meta">'
                        f'<div class="doc-name" title="{d["filename"]}">{d["filename"]}</div>'
                        f'<div class="doc-sub">{d["num_chunks"]} chunks · {d.get("embedding_model","")}'
                        f'{selected_tag}</div>'
                        f'</div></div>', unsafe_allow_html=True)
                    row_pick, row_dl, row_rename, row_del = st.columns([5.2, 1.2, 1.2, 1.2])
                    with row_pick:
                        checked = st.checkbox("Use in this chat", value=is_selected,
                                              key=f"doc_pick_{d['id']}", label_visibility="collapsed")
                        if checked:
                            picked.append(d["id"])
                    with row_dl:
                        src_path = user_store.get_document_source_path(d["id"], user_id)
                        # Guard against re-reading a huge file into memory on
                        # every sidebar rerun — Streamlit's download_button needs
                        # the bytes up front (no true lazy download), so cap what
                        # gets auto-loaded here; bigger originals still show a
                        # button, just disabled with an explanatory tooltip.
                        ok = src_path and os.path.exists(src_path) and os.path.getsize(src_path) < 15_000_000
                        if ok:
                            with open(src_path, "rb") as _f:
                                st.download_button("", data=_f.read(), file_name=d["filename"],
                                                   key=f"doc_dl_{d['id']}", icon=":material/download:",
                                                   help="Download original file", use_container_width=True)
                        else:
                            st.button("", key=f"doc_dl_ph_{d['id']}", icon=":material/download:", disabled=True,
                                     help="Original file not available" if not src_path
                                          else "File too large for quick download here",
                                     use_container_width=True)
                    with row_rename:
                        if st.button("", key=f"doc_rename_btn_{d['id']}", icon=":material/edit:",
                                     help="Rename", use_container_width=True):
                            st.session_state[f"_renaming_{d['id']}"] = True
                    with row_del:
                        if st.button("", key=f"doc_del_btn_{d['id']}", icon=":material/delete:",
                                     help="Delete", use_container_width=True):
                            st.session_state[f"_confirm_del_{d['id']}"] = True

                    if st.session_state.get(f"_renaming_{d['id']}"):
                        new_name = st.text_input("New name", value=d["filename"],
                                                 key=f"doc_rename_input_{d['id']}",
                                                 label_visibility="collapsed")
                        c_save, c_cancel = st.columns(2)
                        if c_save.button("Save", key=f"doc_rename_save_{d['id']}", use_container_width=True):
                            from db.user_store import rename_document
                            rename_document(d["id"], user_id, new_name)
                            st.session_state.pop(f"_renaming_{d['id']}", None)
                            st.rerun()
                        if c_cancel.button("Cancel", key=f"doc_rename_cancel_{d['id']}", use_container_width=True):
                            st.session_state.pop(f"_renaming_{d['id']}", None)
                            st.rerun()

                    if st.session_state.get(f"_confirm_del_{d['id']}"):
                        st.warning(f"Delete **{d['filename']}**? This can't be undone.")
                        c_yes, c_no = st.columns(2)
                        if c_yes.button("Yes, delete", key=f"doc_del_yes_{d['id']}", use_container_width=True):
                            from db.user_store import delete_document
                            delete_document(d["id"], user_id)
                            st.session_state.pop(f"_confirm_del_{d['id']}", None)
                            st.session_state.pop(f"chat_doc_ids", None)
                            st.success(f"Deleted {d['filename']}.")
                            st.rerun()
                        if c_no.button("Cancel", key=f"doc_del_no_{d['id']}", use_container_width=True):
                            st.session_state.pop(f"_confirm_del_{d['id']}", None)
                            st.rerun()

            if st.button("Build Knowledge Base from Selection", use_container_width=True, key="apply_docs_btn"):
                session_id = st.session_state.get("chat_session_id")
                if session_id and picked:
                    title = ", ".join(next(x["filename"] for x in docs if x["id"] == i) for i in picked[:2])
                    if len(picked) > 2: title += f" +{len(picked)-2} more"
                    user_store.rename_session(session_id, title)
                apply_doc_selection(user_id, session_id, picked)
                st.rerun()

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
        qa = user_store.get_all_qa_for_user(user_id)
        if qa:
            import json
            st.download_button(
                "Export my Q&A history", data=json.dumps(qa, indent=2, ensure_ascii=False).encode("utf-8"),
                file_name="my_qa_history.json", mime="application/json",
                use_container_width=True, key="export_qa_btn")


def _render_source_citation(c: dict, key_prefix: str, user_id):
    """One citation row: filename + page, with a small button that renders
    the actual PDF page (highlighted) inline when clicked. True CSS ':hover'
    can't trigger server-side rendering in Streamlit, so this is click-to-
    reveal rather than hover-to-reveal — functionally the same idea (no
    need to leave the answer to go find the source) without depending on
    something Streamlit can't actually do."""
    filename = c.get("source", "?")
    page = c.get("page_number", "?")
    from utils.helpers import source_confidence
    conf = source_confidence(c)
    conf_badge = (f' &nbsp;<span class="badge badge-{conf["label"].lower() if conf["label"]!="Medium" else "med"}" '
                  f'style="font-size:.72rem;padding:.1rem .55rem">{conf["pct"]}% match</span>') if conf else ""
    st.markdown(
        f'<div class="src-row">'
        f'<div class="src-row-head"><b>{filename}</b> · Page {page}{conf_badge}</div>'
        f'<div class="cite-snippet">{c.get("text","")[:280]}...</div>'
        f'</div>', unsafe_allow_html=True)
    is_pdf_source = filename.lower().endswith(".pdf")
    show_key = f"_showpdf_{key_prefix}"
    if is_pdf_source:
        if st.button("View original page", key=f"pdfbtn_{key_prefix}", icon=":material/visibility:",
                     help="View this page in the PDF"):
            st.session_state[show_key] = not st.session_state.get(show_key, False)
    else:
        # .txt/.docx sources never have a rendered page image to show — no
        # button at all, rather than one that always dead-ends into "not
        # available" and reads as broken.
        st.caption("Page preview is only available for PDF sources.")

    if is_pdf_source and st.session_state.get(show_key):
        from db import user_store
        from utils.pdf_highlight import render_highlighted_page
        # Prefer the doc_id attached directly to the chunk (see
        # load_documents_chunks) — that survives a rename. Chunks that
        # don't carry one (e.g. web-search results, or chunks from a batch
        # run that hasn't been through that loader) fall back to matching
        # by filename, same as before.
        doc_id = c.get("_doc_id")
        if not doc_id:
            doc_lookup = {d["filename"]: d["id"] for d in user_store.list_user_documents(user_id)}
            doc_id = doc_lookup.get(filename)
        source_path = user_store.get_document_source_path(doc_id, user_id) if doc_id else None
        if not source_path:
            st.caption("Original PDF isn't available for this document anymore.")
        else:
            img = render_highlighted_page(source_path, page, c.get("text", ""))
            if img:
                st.image(img, caption=f"{filename} — page {page}", use_container_width=True)
            else:
                st.caption("Couldn't render that page.")


def _format_ts(raw) -> str:
    """Best-effort HH:MM from whatever timestamp format the DB stored —
    purely cosmetic, never raises."""
    if not raw:
        return ""
    try:
        from datetime import datetime
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
            try:
                return datetime.strptime(str(raw)[:len(fmt.replace('%f',''))+6], fmt).strftime("%H:%M")
            except ValueError:
                continue
        return str(raw)[11:16] if len(str(raw)) >= 16 else ""
    except Exception:
        return ""


def _status_label(tool: str, inp: str) -> str:
    """Turn a raw tool call into a short, human status line — this is what
    keeps changing in the status widget while the agent works, instead of
    one static 'thinking' message sitting there for the whole request."""
    labels = {
        "retrieve_documents": f"Searching your documents for \"{inp}\"…",
        "web_search":         f"Searching the web for \"{inp}\"…",
        "read_url":           "Reading a web page…",
        "refine_query":       "Refining the search…",
        "summarise_context":  "Summarising what was found…",
        "final_answer":       "Writing the answer…",
    }
    return labels.get(tool, f"{tool.replace('_',' ').title()}…")


def _render_regenerate_row(msg: dict, provider: str, key_prefix: str):
    """Icon-only 'try again with a different model' button. Clicking it is
    itself the 'this wasn't good enough' signal (logged automatically as
    negative feedback — no separate thumbs-down needed), then re-answers
    the SAME question from the SAME retrieved sources on a different LLM,
    so it stays fast — no re-running retrieval or the reasoning loop."""
    chunks = msg.get("sources", [])
    if not chunks:
        return
    tried = msg.setdefault("_tried_providers", [msg.get("_provider", provider)])
    prev_conf = msg.get("_confidence", {}).get("score") if msg.get("_confidence") else None

    if st.button("", key=f"regen_{key_prefix}", icon=":material/refresh:",
                 help="Regenerate this answer with a different model"):
        from llm.regenerate import regenerate
        from utils.feedback_store import store_feedback
        with st.spinner("Trying a different model..."):
            store_feedback(msg.get("_question", ""), msg["content"], chunks, rating=-1,
                           provider=msg.get("_provider", provider))
            res = regenerate(msg.get("_question", ""), chunks, tried,
                             msg.get("_provider", provider), response_style="concise")
        msg["content"]     = res["answer"]
        msg["_provider"]   = res["provider"]
        msg["_confidence"] = res["confidence"]
        msg["_tried_providers"] = tried + [res["provider"]]
        st.rerun()

    if len(tried) > 1:
        note = f"Tried: {', '.join(tried)}"
        if prev_conf is not None and msg.get("_confidence"):
            new_conf = msg["_confidence"].get("score")
            if isinstance(new_conf, int) and new_conf >= 0:
                note += f"  ·  confidence now {new_conf}/10"
        st.caption(note)


def render_chat_mode(web_searcher, provider: str, streaming: bool):
    user_id = st.session_state.get("user_id")

    if "chat_session_id" not in st.session_state:
        from db.user_store import create_chat_session
        st.session_state.chat_session_id = create_chat_session(user_id)
        st.session_state.chat_history = []
        st.session_state.chat_doc_ids = []

    _render_sidebar(user_id)

    retriever = st.session_state.get("retriever")
    reranker  = st.session_state.get("reranker_obj")
    embedder  = st.session_state.get("embedder")

    if not retriever:
        st.markdown(
            '<div class="empty-state-cta-wrap">'
            '<div class="empty-illustration">'
            '<svg width="40" height="40" viewBox="0 0 24 24" fill="none">'
            '<path d="M6 2h9l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" fill="white"/>'
            '<path d="M15 2v5h5" fill="white" opacity=".6"/></svg></div>'
            '<div class="empty-state-title">No documents selected yet</div>'
            '<div class="empty-state-sub">Upload a document to begin chatting — pick one or more '
            'files from the sidebar, or drop a new one in.</div></div>',
            unsafe_allow_html=True)
        return

    if st.session_state.pop("_docs_just_readied", False):
        st.markdown(
            '<div class="ready-banner">&nbsp;<b>Your documents are ready.</b> Ask anything below.</div>',
            unsafe_allow_html=True)

    build_status = st.session_state.pop("_last_build_status", None)
    if build_status:
        st.markdown(
            '<div class="helper-note" style="background:rgba(34,197,94,.08);'
            'border-color:rgba(34,197,94,.25)">'
            f'<b>Knowledge build status</b> &nbsp;·&nbsp; '
            f'<b>{build_status["files"]}</b> file(s) &nbsp;·&nbsp; '
            f'<b>{build_status["chunks"]}</b> chunks &nbsp;·&nbsp; '
            f'model: <b>{build_status["model"]}</b> &nbsp;·&nbsp; '
            f'{build_status["elapsed"]:.1f}s'
            '</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="helper-note">ℹ️ Responses are generated only from the selected document(s) '
        'in the sidebar.</div>', unsafe_allow_html=True)

    if "chat_conv_memory" not in st.session_state:
        from agent.conversation_memory import ConversationMemory
        st.session_state.chat_conv_memory = ConversationMemory(max_turns_in_context=6)
    if st.session_state.get("chat_agent") is None:
        from agent.react_agent import AgenticRAG
        st.session_state.chat_agent = AgenticRAG(
            retriever=retriever, reranker=reranker,
            web_searcher=web_searcher, embedder=embedder,
            provider=provider,
            max_iterations=st.session_state.get("chat_max_iter", 2),
            stream=streaming,
            conversation_memory=st.session_state.chat_conv_memory,
            response_style="concise",
            fast_first_step=True,
        )

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("_ts"):
                st.markdown(f'<div class="chat-timestamp">{msg["_ts"]}</div>', unsafe_allow_html=True)
            if msg["role"] == "assistant":
                _render_regenerate_row(msg, provider, key_prefix=f"hist_{id(msg)}")

    if "chat_semantic_cache" not in st.session_state:
        from retrieval.semantic_cache import SemanticCache
        st.session_state.chat_semantic_cache = SemanticCache()
    sem_cache = st.session_state.chat_semantic_cache

    question = st.chat_input("Ask anything about your uploaded documents...")

    if question:
        from datetime import datetime
        now_ts = datetime.now().strftime("%H:%M")
        st.session_state.chat_history.append({"role": "user", "content": question, "_ts": now_ts})
        with st.chat_message("user"):
            st.markdown(question)
            st.markdown(f'<div class="chat-timestamp">{now_ts}</div>', unsafe_allow_html=True)

        # Cache is scoped to the current document selection — same question
        # against a different set of files is a different question.
        cache_key = f"{sorted(st.session_state.get('chat_doc_ids', []))}::{question}"
        cached = sem_cache.lookup(cache_key)

        agent = st.session_state.chat_agent

        # Appended NOW (empty) and filled in below — this is deliberate: it
        # gives the message a stable id() that matches exactly what the
        # history loop above will use on any rerun (e.g. right after a
        # feedback click), so a Good/Poor rating doesn't "lose" the turn or
        # reset to unrated because the key changed underneath it.
        msg = {"role": "assistant", "content": "", "trace": [], "sources": [], "_question": question,
               "_ts": now_ts}
        st.session_state.chat_history.append(msg)
        fb_key = f"hist_{id(msg)}"

        with st.chat_message("assistant"):
            answer_placeholder = st.empty()
            trace_steps, full_answer, result_chunks = [], "", []

            if cached:
                full_answer   = cached["answer"]
                result_chunks = cached.get("chunks", [])
                trace_steps   = []
                answer_placeholder.markdown(full_answer)
                st.caption(f"Answered from cache (similar to: \"{cached['_cache_original'].split('::',1)[-1][:60]}\")")
            elif streaming:
                # Status label keeps changing as each real reasoning step
                # happens (retrieving, searching, refining, synthesising) —
                # instead of one static "Agent reasoning" line that just
                # sits there while an expander quietly fills up behind it.
                with st.status("Reading your documents...", expanded=False) as status:
                    for event_type, payload in agent.run_streaming(question):
                        if event_type == "trace":
                            tool = payload.get("tool", "")
                            inp  = payload.get("input", "")[:60]
                            status.update(label=_status_label(tool, inp))
                            trace_steps.append(payload)
                        elif event_type == "token":
                            full_answer += payload
                            answer_placeholder.markdown(full_answer + "▌")
                        elif event_type == "done":
                            full_answer   = payload["answer"]
                            result_chunks = payload.get("chunks", [])
                    status.update(label="Answer ready", state="complete")
                answer_placeholder.markdown(full_answer)
            else:
                with st.status("Reading your documents...", expanded=False) as status:
                    result        = agent.run(question, status_callback=lambda m: status.update(label=m))
                    full_answer   = result["answer"]
                    result_chunks = result.get("chunks", [])
                    trace_steps   = result.get("trace", [])
                    status.update(label="Answer ready", state="complete")
                answer_placeholder.markdown(full_answer)

            if not cached:
                sem_cache.store(cache_key, {"answer": full_answer, "chunks": result_chunks})

            msg["content"]   = full_answer
            msg["trace"]     = trace_steps
            msg["sources"]   = result_chunks
            msg["_provider"] = provider
            st.markdown(f'<div class="chat-timestamp">{now_ts}</div>', unsafe_allow_html=True)
            _render_regenerate_row(msg, provider, key_prefix=fb_key)

            # There's no separate Good/Poor button anymore — Regenerate IS
            # the "this wasn't good enough" signal (it logs rating=-1 when
            # clicked). So an answer that's never regenerated is logged as
            # implicitly good right away; if the person does regenerate,
            # that adds a negative record on top of this one. Either way
            # every answer ends up with real feedback data instead of the
            # admin dashboard only ever hearing about complaints.
            if not cached:
                try:
                    from utils.feedback_store import store_feedback
                    store_feedback(question, full_answer, result_chunks, rating=1,
                                   provider=provider, comment="auto: not regenerated")
                except Exception as e:
                    logger.warning(f"Implicit feedback log failed: {e}")

        if user_id:
            try:
                from db.user_store import save_qa_turn
                sources = ", ".join(sorted({c.get("source","") for c in result_chunks}))
                save_qa_turn(user_id, st.session_state.chat_session_id, question, full_answer,
                            doc_sources=sources, provider=provider, mode="chat")
            except Exception as e:
                logger.warning(f"Could not save chat turn: {e}")