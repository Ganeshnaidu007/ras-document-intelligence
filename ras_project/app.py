"""app.py — RAS Document Intelligence  |  3-phase wizard UI"""
import os, sys, warnings, concurrent.futures
sys.path.insert(0, os.path.dirname(__file__))
import utils.model_cache  # noqa: F401 — sets HF_HOME etc. before any model import, anywhere
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
warnings.filterwarnings("ignore", category=FutureWarning,  module="transformers")
warnings.filterwarnings("ignore", category=UserWarning,    module="huggingface_hub")

import streamlit as st

st.set_page_config(
    page_title="RAS — Document Intelligence",
    page_icon=None, layout="wide",
    initial_sidebar_state="expanded",
)

from ui.styles   import GLOBAL_CSS
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

from ui.upload_ui import render_source_upload, render_question_upload
from ui.output_ui import render_output_section
from utils.logger import get_logger
from config.settings import DEFAULT_SETTINGS
logger = get_logger(__name__)


# ── Session state ──────────────────────────────────────────────────────────────
def _init():
    D = {
        "source_files": [], "question_file": None,
        "chunking_method":    DEFAULT_SETTINGS["chunking_method"],
        "chunk_size":         DEFAULT_SETTINGS["chunk_size"],
        "chunk_overlap":      DEFAULT_SETTINGS["chunk_overlap"],
        "embedding_model":    DEFAULT_SETTINGS["embedding_model"],
        "retrieval_strategy": DEFAULT_SETTINGS["retrieval_strategy"],
        "reranking_enabled":  DEFAULT_SETTINGS["reranking_enabled"],
        "reranking_model":    DEFAULT_SETTINGS["reranking_model"],
        "ocr_enabled":        DEFAULT_SETTINGS["ocr_enabled"],
        "ocr_engine":         DEFAULT_SETTINGS["ocr_engine"],
        "language":           DEFAULT_SETTINGS["language"],
        "output_format":      DEFAULT_SETTINGS["output_format"],
        "multi_query_enabled":DEFAULT_SETTINGS["multi_query_enabled"],
        "real_time_search":   False,
        "llm_provider":       "groq",
        "agentic_mode":       True,
        "streaming_enabled":  True,
        "confidence_enabled": True,
        "response_style":     "concise",   # "concise" (default) or "detailed" — see Agent Settings
        "agent_max_iter":     5,
        "chat_max_iter":      2,   # chat had been silently reusing agent_max_iter
                                   # (defaults to 5) — every reply paid for up to
                                   # 5 reasoning round-trips before even starting
                                   # to write the answer. Chat gets its own lower
                                   # cap since replies need to feel fast.
        "app_mode":           "batch",
        "indexes_built":      False,
        "retriever": None, "reranker_obj": None, "embedder": None,
        "output_data": None, "processing_done": False,
        "job_history": [],
        "auto_chunking":      True,
        "fact_check_enabled": False,
        "semantic_cache":     None,
        "doc_summaries":      [],
        "speed_mode":         False,
        # wizard state
        "wizard_phase":       1,          # 1=upload  2=configure  3=results
        "auto_config":        None,       # dict of auto-detected settings
        "config_confirmed":   False,
        "doc_preview":        None,       # {pages, lang, words, tables}
    }
    for k, v in D.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── Top bar ─────────────────────────────────────────────────────────────────────
def _topbar():
    mode = st.session_state.app_mode
    c_logo, c_batch, c_chat, c_logout = st.columns([5, 1.3, 1.3, 1.2])

    with c_logo:
        st.markdown(
            '<div class="topbar-left" style="display:flex;align-items:center;height:100%;">'
            '  <div class="logo">R</div>'
            '  <div><div class="product-name">RAS</div>'
            '       <div class="product-sub-title">Document Intelligence</div></div>'
            '</div>', unsafe_allow_html=True)
    with c_batch:
        if st.button("Batch Q&A", key="btn_mode_batch", use_container_width=True,
                    type="primary" if mode == "batch" else "secondary"):
            st.session_state.app_mode = "batch"
            # Coming from chat (or fresh login) means nothing has been
            # uploaded for batch mode yet — don't leave wizard_phase at 3,
            # or the pipeline runs immediately against 0 source files.
            if not st.session_state.get("source_files") or not st.session_state.get("question_file"):
                st.session_state.wizard_phase = 1
                st.session_state.processing_done = False
            st.rerun()
    with c_chat:
        if st.button("Chat Mode", key="btn_mode_chat", use_container_width=True,
                    type="primary" if mode == "chat" else "secondary"):
            st.session_state.app_mode = "chat"
            st.session_state.wizard_phase = 3
            st.rerun()
    with c_logout:
        if st.button("Log out", key="nav_logout_btn", use_container_width=True):
            from auth.auth import logout
            logout()

    st.caption(f"Signed in as **{st.session_state.get('user_name', '')}**")
    st.markdown("---")


# ── Wizard progress bar ──────────────────────────────────────────────────────────
def _wizard_bar():
    pass  # step indicators removed


# ── Phase 1: Upload ──────────────────────────────────────────────────────────────
def _phase1():


    col_src, col_q = st.columns([3, 2])
    with col_src:
        render_source_upload()
    with col_q:
        if st.session_state.app_mode == "batch":
            render_question_upload()
        else:
            st.markdown('<span class="label">Chat Mode</span>', unsafe_allow_html=True)
            st.info("You will type questions directly in the chat interface.")

    st.markdown("---")

    # Ready check
    has_src = bool(st.session_state.source_files)
    has_q   = (st.session_state.app_mode == "chat") or (st.session_state.question_file is not None)

    if has_src and has_q:
        # Doc stats preview
        total_size = sum(getattr(f,"size",0) for f in st.session_state.source_files) / 1024
        n_docs = len(st.session_state.source_files)
        st.markdown(
            f'<div class="doc-stats">'
            f'<span class="ds-item"><strong>{n_docs}</strong> document{"s" if n_docs!=1 else ""}</span>'
            f'<span class="ds-item"><strong>{total_size:.0f} KB</strong> total size</span>'
            f'<span class="ds-item"><strong>{"Batch Q&A" if st.session_state.app_mode=="batch" else "Chat"}</strong> mode</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Continue to Configuration", type="primary", use_container_width=True,
                     key="phase1_next"):
            with st.spinner("Analysing documents and selecting optimal settings..."):
                _run_auto_config()
            st.session_state.wizard_phase = 2
            st.rerun()
    else:
        missing = []
        if not has_src: missing.append("source document")
        if not has_q and st.session_state.app_mode == "batch": missing.append("question file")
        st.markdown(
            f'<div style="font-size:.8rem;color:var(--tx3);padding:.5rem 0">'
            f'Waiting for: {" and ".join(missing)}</div>',
            unsafe_allow_html=True,
        )


# ── Auto-configuration logic ─────────────────────────────────────────────────────
def _run_auto_config():
    """Quick analysis: peek at files without full parse, set recommended settings."""
    import re

    files  = st.session_state.source_files
    total  = sum(getattr(f,"size",0) for f in files) / 1024  # KB
    names  = [f.name.lower() for f in files]
    exts   = [n.rsplit(".",1)[-1] if "." in n else "txt" for n in names]

    # Read a text sample from first file to classify
    sample = ""
    try:
        first = files[0]
        first.seek(0)
        raw = first.read(2048); first.seek(0)
        if exts[0] == "pdf":
            sample = raw.decode("latin-1", errors="ignore")
        else:
            sample = raw.decode("utf-8", errors="ignore")
    except Exception:
        pass

    s = sample.lower()

    # Detect document type
    if any(k in s for k in ["abstract", "arxiv", "doi:", "methodology", "conference", "proceedings"]):
        doc_type = "Research Paper"
        method, size, overlap = "Semantic + Recursive Hybrid", 400, 50
        embedding = "all-MiniLM-L6-v2"
    elif any(k in s for k in ["whereas", "hereinafter", "section", "clause", "agreement", "plaintiff"]):
        doc_type = "Legal Document"
        method, size, overlap = "Paragraph Chunking", 600, 80
        embedding = "all-MiniLM-L6-v2"
    elif any(k in s for k in ["revenue", "fiscal", "earnings", "balance sheet", "q1 ", "q2 ", "ebitda"]):
        doc_type = "Financial Report"
        method, size, overlap = "Recursive Chunking", 500, 60
        embedding = "all-MiniLM-L6-v2"
    elif re.search(r"def |class |import |function\(|<html|public static", s):
        doc_type = "Code / Technical"
        method, size, overlap = "Fixed Chunking", 200, 20
        embedding = "all-MiniLM-L6-v2"
    elif len(files) > 1:
        doc_type = "Mixed Documents"
        method, size, overlap = "Semantic + Recursive Hybrid", 500, 50
        embedding = "all-MiniLM-L6-v2"
    elif total > 500:
        doc_type = "Long Document"
        method, size, overlap = "Recursive Chunking", 500, 75
        embedding = "all-MiniLM-L6-v2"
    else:
        doc_type = "General Text"
        method, size, overlap = "Semantic + Recursive Hybrid", 400, 50
        embedding = "all-MiniLM-L6-v2"

    # Estimate chunks
    words_est  = int(total * 100)
    chunks_est = max(1, words_est // (size // 2))

    # LLM recommendation
    from config.settings import GROQ_API_KEY, GOOGLE_API_KEY
    llm = "gemini" if GOOGLE_API_KEY else ("groq" if GROQ_API_KEY else "groq")

    # Agent iterations
    iters = 4 if total < 200 else 5

    cfg = {
        "doc_type":       doc_type,
        "chunking_method":method,
        "chunk_size":     size,
        "chunk_overlap":  overlap,
        "embedding_model":embedding,
        "retrieval_strategy": "Hybrid Retrieval",
        "reranking_enabled": True,
        "reranking_model":   "BGE Reranker",
        "llm_provider":   llm,
        "agent_max_iter": iters,
        "output_format":  "PDF",
        "ocr_enabled":    any(e == "pdf" for e in exts),
        "total_kb":       round(total, 1),
        "chunks_est":     chunks_est,
        "words_est":      words_est,
        "auto_chunking":  True,
    }

    # Apply to session
    for k in ("chunking_method","chunk_size","chunk_overlap","embedding_model",
              "retrieval_strategy","reranking_enabled","reranking_model",
              "llm_provider","agent_max_iter","output_format","ocr_enabled"):
        st.session_state[k] = cfg[k]

    st.session_state.auto_config = cfg


# ── Phase 2: Configure ───────────────────────────────────────────────────────────
def _phase2():
    cfg = st.session_state.get("auto_config", {})

    # ── Auto-config summary table ──────────────────────────────────────────────
    st.markdown(
        f'<div class="config-panel">'
        f'<h3>Recommended Configuration</h3>'
        f'<table class="cfg-table">'
        f'<thead><tr><th>Setting</th><th>Description</th><th>Value</th><th></th></tr></thead>'
        f'<tbody>'
        f'<tr><td>Document type</td><td>Based on content analysis of your files</td>'
        f'    <td>{cfg.get("doc_type","General")}</td><td><span class="cr-badge-auto">auto</span></td></tr>'
        f'<tr><td>Chunking strategy</td><td>How documents are split into searchable pieces</td>'
        f'    <td>{cfg.get("chunking_method","—")} &middot; {cfg.get("chunk_size","—")} tokens</td><td><span class="cr-badge-auto">auto</span></td></tr>'
        f'<tr><td>Embedding model</td><td>Converts text to vectors for semantic search</td>'
        f'    <td>{cfg.get("embedding_model","—")}</td><td><span class="cr-badge-auto">auto</span></td></tr>'
        f'<tr><td>Retrieval strategy</td><td>How relevant passages are found</td>'
        f'    <td>{cfg.get("retrieval_strategy","—")}</td><td><span class="cr-badge-auto">auto</span></td></tr>'
        f'<tr><td>LLM provider</td><td>Model used to generate answers</td>'
        f'    <td>{cfg.get("llm_provider","groq").title()}</td><td><span class="cr-badge-auto">auto</span></td></tr>'
        f'<tr><td>Estimated index size</td><td>Approximate chunks that will be created</td>'
        f'    <td>~{cfg.get("chunks_est",0)} chunks</td><td></td></tr>'
        f'</tbody></table>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Feature selection ──────────────────────────────────────────────────────
    st.markdown('<span class="label" style="margin-top:1.5rem;display:block">Optional Features</span>',
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.session_state.confidence_enabled = st.toggle(
            "Confidence Scoring",
            value=st.session_state.get("confidence_enabled", True),
            key="feat_conf",
            help="After each answer, scores 0-10 how well it is grounded in your documents. Adds 1 LLM call per question.")
        st.markdown(
            '<div class="feat-desc" style="margin-top:-.25rem">Scores each answer 0–10 on source grounding. '
            '<span style="color:var(--amber);font-size:.68rem">+1 API call/question</span></div>',
            unsafe_allow_html=True)

    with c2:
        st.session_state.fact_check_enabled = st.toggle(
            "Fact Verification",
            value=st.session_state.get("fact_check_enabled", False),
            key="feat_fc",
            help="Extracts every factual claim and checks each against retrieved chunks. Adds 1-2 LLM calls per question.")
        st.markdown(
            '<div class="feat-desc" style="margin-top:-.25rem">Checks every claim against source passages. '
            '<span style="color:var(--amber);font-size:.68rem">+1–2 API calls/question</span></div>',
            unsafe_allow_html=True)

    with c3:
        st.session_state.real_time_search = st.toggle(
            "Web Search",
            value=st.session_state.get("real_time_search", False),
            key="feat_web",
            help="Augments document retrieval with live Google search results. Requires SERP_API_KEY.")
        st.markdown(
            '<div class="feat-desc" style="margin-top:-.25rem">Adds live search results as context. '
            '<span style="color:var(--amber);font-size:.68rem">+2–5s latency/question</span></div>',
            unsafe_allow_html=True)

    # ── ReAct explanation ──────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<span class="label">Agent Settings</span>', unsafe_allow_html=True)

    col_a, col_b = st.columns([2, 3])
    with col_a:
        st.session_state.agentic_mode = st.toggle(
            "Agentic RAG (ReAct loop)",
            value=st.session_state.get("agentic_mode", True),
            key="feat_react",
            help="Enables multi-step reasoning. Agent decides which tools to call each iteration.")

        st.session_state.agent_max_iter = st.slider(
            "Max iterations", 2, 10,
            value=st.session_state.get("agent_max_iter", 5),
            key="iter_slider",
            help="Each iteration = one think→act→observe cycle.")

        st.session_state.llm_provider = st.selectbox(
            "LLM Provider",
            ["groq", "gemini", "openrouter", "openai"],
            index=["groq","gemini","openrouter","openai"].index(
                st.session_state.get("llm_provider","groq")),
            key="prov_select")

    with col_b:
        st.session_state.response_style = st.radio(
            "Answer style",
            ["concise", "detailed"],
            index=["concise","detailed"].index(st.session_state.get("response_style","concise")),
            format_func=lambda v: "Concise — direct answer, no forced sections" if v == "concise"
                                   else "Detailed — full report (Summary, Key Findings, Evidence, Limitations)",
            key="resp_style_radio",
            help="Concise answers a question in a few plain paragraphs. Detailed always "
                 "produces a longer structured report, even for simple questions.")

    # ── Advanced options expander ──────────────────────────────────────────────
    with st.expander("Advanced — override auto-selected settings", expanded=False):
        from ui.settings_ui import (render_chunking_settings, render_embedding_settings,
                                     render_retrieval_settings, render_ocr_settings,
                                     render_output_settings)
        tab_chunk, tab_embed, tab_ret, tab_ocr, tab_out = st.tabs(
            ["Chunking", "Embedding", "Retrieval", "OCR", "Output"])
        with tab_chunk: render_chunking_settings()
        with tab_embed: render_embedding_settings()
        with tab_ret:   render_retrieval_settings()
        with tab_ocr:   render_ocr_settings()
        with tab_out:   render_output_settings()

    st.markdown("---")

    # ── Action row ─────────────────────────────────────────────────────────────
    col_back, col_go = st.columns([1, 3])
    with col_back:
        if st.button("Back", key="phase2_back", use_container_width=True):
            st.session_state.wizard_phase = 1
            st.rerun()
    with col_go:
        label = "Start Analysis" if st.session_state.app_mode == "batch" else "Build Index & Chat"
        if st.button(label, type="primary", use_container_width=True, key="phase2_go"):
            if st.session_state.app_mode == "batch":
                st.session_state.wizard_phase = 3
                st.rerun()
            else:
                with st.spinner("Building indexes..."):
                    _build_and_store_indexes()
                st.session_state.wizard_phase = 3
                st.rerun()


# ── Phase 3: Results ─────────────────────────────────────────────────────────────
def _phase3():
    if st.session_state.app_mode == "chat":
        _chat_phase()
        return

    if not st.session_state.processing_done:
        _run_pipeline_phase3()
    else:
        # Show restart button at top
        col_r, col_d, _ = st.columns([1, 1, 3])
        with col_r:
            if st.button("New analysis", key="restart_btn", use_container_width=True):
                for k in ("processing_done","output_data","wizard_phase","auto_config",
                          "indexes_built","retriever","reranker_obj","embedder","doc_summaries"):
                    if k == "wizard_phase": st.session_state[k] = 1
                    elif k in ("processing_done","indexes_built"): st.session_state[k] = False
                    else: st.session_state[k] = None
                st.rerun()
        with col_d:
            if st.session_state.output_data:
                d = st.session_state.output_data
                st.download_button(
                    f"Download {st.session_state.output_format}",
                    data=d["bytes"], file_name=f"answers.{d['ext']}",
                    mime=d["mime"], type="primary", use_container_width=True)
        st.markdown("---")
        render_output_section()


def _run_pipeline_phase3():
    """Run the full pipeline with a timeline progress display."""
    from retrieval.hybrid_retriever import HybridRetriever
    from retrieval.reranker         import Reranker
    from retrieval.realtime_search  import RealTimeSearcher
    from parsers.question_parser    import QuestionParser
    from outputs.pdf_export  import PDFExporter
    from outputs.docx_export import DOCXExporter
    from outputs.txt_export  import TXTExporter
    from outputs.json_export import JSONExporter
    from utils.helpers       import save_uploaded_file, cleanup_temp_files

    # ── Timeline placeholder ───────────────────────────────────────────────────
    steps = [
        ("parse",     "Parsing documents"),
        ("classify",  "Classifying & configuring"),
        ("embed",     "Chunking & embedding"),
        ("index",     "Building search index"),
        ("questions", "Parsing questions"),
        ("retrieve",  "Retrieving passages"),
        ("generate",  "Generating answers"),
        ("score",     "Scoring confidence"),
        ("export",    "Exporting results"),
    ]
    tl_ph  = st.empty()
    prog   = st.progress(0)

    def _render_timeline(done_up_to: int, detail: str = ""):
        html = '<div class="timeline">'
        for i, (_, label) in enumerate(steps):
            if i < done_up_to:     cls = "tl-step tl-done";   icon = "&#10003;"
            elif i == done_up_to:  cls = "tl-step tl-active"; icon = "&#9679;"
            else:                  cls = "tl-step";             icon = str(i+1)
            det = f'<div class="tl-detail">{detail}</div>' if (i == done_up_to and detail) else ""
            html += (f'<div class="{cls}"><div class="tl-icon">{icon}</div>'
                     f'<div><div class="tl-label">{label}</div>{det}</div></div>')
            if i < len(steps)-1:
                html += '<div class="tl-connector"></div>'
        html += '</div>'
        tl_ph.markdown(html, unsafe_allow_html=True)

    def _step(idx: int, pct: int, detail: str = ""):
        _render_timeline(idx, detail)
        prog.progress(pct)

    if st.session_state.get("semantic_cache") is None:
        from retrieval.semantic_cache import SemanticCache
        st.session_state.semantic_cache = SemanticCache()
    sem_cache = st.session_state.semantic_cache

    # Guard: never let this run against an empty upload. This is the
    # actual fix for the "0 files" / BM25 ZeroDivisionError crash — it
    # happened when wizard_phase got stuck at 3 (e.g. right after login,
    # or after switching modes) with no files ever uploaded.
    if not st.session_state.get("source_files") or not st.session_state.get("question_file"):
        st.warning("No documents or question file found for this session — please upload them first.")
        st.session_state.wizard_phase = 1
        st.session_state.processing_done = False
        st.rerun()
        return

    err_ph = st.empty()
    try:
        # ── 1. Parse ───────────────────────────────────────────────────────────
        _step(0, 5, f"Reading {len(st.session_state.source_files)} file(s)...")
        source_paths, raw_docs = _parse_source_docs()

        # ── 2. Classify ────────────────────────────────────────────────────────
        _step(1, 12, "Detecting document type...")
        if st.session_state.get("auto_chunking"):
            _auto_classify(raw_docs)

        # ── 3. Embed ───────────────────────────────────────────────────────────
        _step(2, 25, f"Embedding with {st.session_state.embedding_model}...")
        embedder, h_idx, b_idx, all_chunks, cache_hits = _build_indexes(source_paths, raw_docs)
        cache_note = f" ({cache_hits} cached)" if cache_hits else ""

        # ── 4. Index ───────────────────────────────────────────────────────────
        _step(3, 45, f"{len(all_chunks)} chunks indexed{cache_note}")
        retriever = HybridRetriever(h_idx, b_idx, embedder, st.session_state.retrieval_strategy)
        reranker  = Reranker(st.session_state.reranking_enabled, st.session_state.reranking_model)
        st.session_state.retriever    = retriever
        st.session_state.reranker_obj = reranker
        st.session_state.embedder     = embedder
        st.session_state.indexes_built = True

        # Doc summaries
        try:
            from ingestion.document_summarizer import summarize_document
            st.session_state.doc_summaries = [summarize_document(d) for d in raw_docs]
        except Exception: pass

        # ── 5. Parse questions ─────────────────────────────────────────────────
        _step(4, 50, "Reading question file...")
        q_path = save_uploaded_file(st.session_state.question_file, "questions",
                                    user_id=st.session_state.get("user_id"))
        ext    = os.path.splitext(q_path)[1].lower()
        if ext == ".pdf":
            from ingestion.pdf_parser import PDFParser as _QP
            q_text = "\n".join(p["text"] for p in _QP(ocr_enabled=False).parse(q_path)["pages"])
        elif ext in (".docx",".doc"):
            from ingestion.docx_parser import DOCXParser as _QD
            q_text = "\n".join(p["text"] for p in _QD().parse(q_path)["pages"])
        else:
            q_text = open(q_path, encoding="utf-8", errors="ignore").read()
        questions = QuestionParser().parse(q_text)

        # ── Semantic cache pre-check ───────────────────────────────────────────
        cache_hits_q, questions_to_run, cached_answers = 0, [], {}
        for q in questions:
            hit = sem_cache.lookup(q["text"]) if sem_cache else None
            if hit: cached_answers[q["text"]] = hit; cache_hits_q += 1
            else:   questions_to_run.append(q)

        searcher  = RealTimeSearcher() if st.session_state.real_time_search else None
        provider  = st.session_state.llm_provider
        streaming = st.session_state.streaming_enabled
        agentic   = st.session_state.agentic_mode
        answered  = []

        # ── 6. Retrieve + Generate ─────────────────────────────────────────────
        _step(5, 55, f"{len(questions)} question(s) · {cache_hits_q} from cache")

        if agentic and questions_to_run:
            from agent.react_agent         import AgenticRAG
            from agent.conversation_memory import ConversationMemory
            conv_mem = ConversationMemory()
            resp_style = st.session_state.get("response_style", "concise")

            def _run_one(q_item):
                return AgenticRAG(
                    retriever=retriever, reranker=reranker,
                    web_searcher=searcher, embedder=embedder,
                    provider=provider,
                    max_iterations=st.session_state.get("agent_max_iter", 5),
                    stream=False, conversation_memory=conv_mem,
                    response_style=resp_style,
                ).run(q_item["text"])

            _step(6, 60, f"Running ReAct agent on {len(questions_to_run)} question(s)...")

            if streaming and len(questions_to_run) == 1 and not cached_answers:
                q  = questions_to_run[0]
                ag = AgenticRAG(retriever=retriever, reranker=reranker,
                                web_searcher=searcher, embedder=embedder,
                                provider=provider,
                                max_iterations=st.session_state.get("agent_max_iter", 5),
                                stream=True, conversation_memory=conv_mem,
                                response_style=resp_style)
                tl_ph.empty()
                trace_ph = st.expander("Agent reasoning trace", expanded=False)
                ans_ph   = st.empty()
                full_ans, res_chunks = "", []
                for etype, payload in ag.run_streaming(q["text"], lambda m: None):
                    if etype == "trace":
                        with trace_ph:
                            it  = payload.get("iteration","?")
                            tl  = payload.get("tool","")
                            inp = payload.get("input","")[:80]
                            thx = payload.get("thought","")[:120]
                            st.markdown(
                                f'<div class="fc-row" style="padding:.4rem 0">'
                                f'<span style="color:var(--tx3);font-size:.7rem;font-family:monospace">'
                                f'[{it}] {tl}</span> '
                                f'<span style="color:var(--tx2);font-size:.78rem">{inp}</span>'
                                f'<div style="font-size:.72rem;color:var(--tx3);font-style:italic;margin-top:.15rem">{thx}</div>'
                                f'</div>', unsafe_allow_html=True)
                    elif etype == "token":
                        full_ans += payload
                        ans_ph.markdown(
                            f'<div class="ans-card"><div class="ans-body">{full_ans}&#9646;</div></div>',
                            unsafe_allow_html=True)
                    elif etype == "done":
                        full_ans   = payload["answer"]
                        res_chunks = payload["chunks"]
                        ans_ph.markdown(
                            f'<div class="ans-card"><div class="ans-body">{full_ans}</div></div>',
                            unsafe_allow_html=True)
                ad = {"number": q.get("number"), "prefix": q.get("prefix",""),
                      "question": q["text"], "answer": full_ans,
                      "citations": "", "chunks": res_chunks,
                      "_provider": provider}
                if sem_cache: sem_cache.store(q["text"], ad)
                answered.append(ad)
            else:
                with concurrent.futures.ThreadPoolExecutor(
                        max_workers=min(len(questions_to_run), 5)) as ex:
                    futs = {ex.submit(_run_one, q): q for q in questions_to_run}
                    for i, (fut, q) in enumerate(futs.items()):
                        r2  = fut.result()
                        pct = 60 + int(25*(i+1)/max(len(questions_to_run),1))
                        _step(6, pct, f"Answered {i+1}/{len(questions_to_run)}")
                        ad = {"number": q.get("number"), "prefix": q.get("prefix",""),
                              "question": q["text"], "answer": r2["answer"],
                              "citations": "", "chunks": r2["chunks"],
                              "_provider": provider}
                        if sem_cache: sem_cache.store(q["text"], ad)
                        answered.append(ad)

        elif questions_to_run:
            from retrieval.multi_query import MultiQueryExpander
            from llm.answer_generator  import AnswerGenerator
            _step(6, 60, f"Retrieving for {len(questions_to_run)} question(s)...")
            emq = MultiQueryExpander(st.session_state.multi_query_enabled)
            gen = AnswerGenerator(provider=provider, response_style=st.session_state.get("response_style", "concise"))

            def _ret(q):
                rcs = []
                for qry in emq.expand(q["text"]): rcs.extend(retriever.retrieve(qry, top_k=20))
                if searcher: rcs.extend(searcher.to_chunks(q["text"], num_results=3))
                seen, uniq = set(), []
                for c in rcs:
                    cid = c.get("chunk_id", c["text"][:40])
                    if cid not in seen: seen.add(cid); uniq.append(c)
                return reranker.rerank(q["text"], uniq, top_k=8)

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
                bests = list(ex.map(_ret, questions_to_run))
            _step(6, 75, f"Generating {len(questions_to_run)} answers...")
            for q, best, ans in zip(questions_to_run, bests,
                                    gen.generate_batch([(q["text"],b) for q,b in zip(questions_to_run,bests)])):
                ad = {"number": q.get("number"), "prefix": q.get("prefix",""),
                      "question": q["text"], "answer": ans,
                      "citations": "", "chunks": best,
                      "_provider": provider}
                if sem_cache: sem_cache.store(q["text"], ad)
                answered.append(ad)

        # There's no separate Good/Poor button in batch mode either —
        # Regenerate (which logs rating=-1 when clicked) is the only
        # explicit signal now. So every freshly-generated answer is logged
        # as implicitly good right away; a later regenerate click adds a
        # negative record on top. This is skipped for cache hits, since
        # those were already logged the first time they were generated.
        if answered:
            try:
                from utils.feedback_store import store_feedback
                for a in answered:
                    store_feedback(a["question"], a["answer"], a.get("chunks", []),
                                   rating=1, provider=a.get("_provider", provider),
                                   comment="auto: not regenerated")
            except Exception as e:
                logger.warning(f"Implicit batch feedback log failed: {e}")

        # Merge cache + fresh
        merged = []
        for q in questions:
            if q["text"] in cached_answers:
                ca = cached_answers[q["text"]]
                merged.append({"number": q.get("number"), "prefix": q.get("prefix",""),
                                "question": q["text"], "answer": ca["answer"],
                                "citations": ca.get("citations",""), "chunks": ca.get("chunks",[]),
                                "_cache_hit": True, "_cache_score": ca.get("_cache_score",0),
                                "_cache_original": ca.get("_cache_original","")})
            else:
                for a in answered:
                    if a["question"] == q["text"]: merged.append(a); break
        answered = merged if merged else answered

        # Save each Q&A turn for this user (survives refresh/restart)
        user_id = st.session_state.get("user_id")
        if user_id and answered:
            from db.user_store import save_qa_turn
            for a in answered:
                save_qa_turn(user_id, None, a["question"], a.get("answer", ""),
                            doc_sources=", ".join(sorted({c.get("source","") for c in a.get("chunks",[])})),
                            provider=st.session_state.get("llm_provider",""), mode="batch")

        # ── 8. Confidence scoring ──────────────────────────────────────────────
        if st.session_state.confidence_enabled and answered:
            _step(7, 90, f"Scoring {len(answered)} answer(s)...")
            try:
                from llm.confidence_scorer import score_batch
                scores = score_batch([(a["question"],a.get("chunks",[]),a["answer"]) for a in answered])
                for a, sc in zip(answered, scores): a["confidence"] = sc
            except Exception as e:
                logger.warning(f"Confidence scoring: {e}")

        # ── 9. Export ──────────────────────────────────────────────────────────
        _step(8, 97, f"Writing {st.session_state.output_format} file...")
        fmt      = st.session_state.output_format
        exporter = {"PDF": PDFExporter,"DOCX": DOCXExporter,
                    "JSON": JSONExporter,"TXT": TXTExporter}[fmt]()
        out_bytes, mime, ext_out = exporter.export(answered)

        _render_timeline(len(steps), "Complete")
        prog.progress(100)

        st.session_state.output_data = {
            "bytes": out_bytes, "mime": mime, "ext": ext_out,
            "answered_questions": answered,
        }
        st.session_state.processing_done = True
        st.session_state.job_history.append({
            "num_sources": len(source_paths), "num_questions": len(questions),
            "format": fmt, "mode": "agentic" if agentic else "classic",
            "cache_hits": cache_hits_q,
        })
        cleanup_temp_files(user_id=st.session_state.get("user_id"))
        st.rerun()

    except Exception as e:
        from utils.safe_error import show_safe_error
        prog.empty(); tl_ph.empty()
        show_safe_error("Something went wrong while processing your documents.",
                        exc=e, placeholder=err_ph)
        cleanup_temp_files(user_id=st.session_state.get("user_id"))


def _chat_phase():
    from ui.chat_ui import render_chat_mode
    searcher = None
    if st.session_state.real_time_search:
        from retrieval.realtime_search import RealTimeSearcher
        searcher = RealTimeSearcher()
    render_chat_mode(
        web_searcher=searcher,
        provider=st.session_state.llm_provider,
        streaming=st.session_state.streaming_enabled,
    )


# ── Shared pipeline helpers ──────────────────────────────────────────────────────
def _parse_source_docs():
    from ingestion.pdf_parser   import PDFParser
    from ingestion.docx_parser  import DOCXParser
    from ingestion.text_cleaner import TextCleaner
    from utils.helpers          import save_uploaded_file
    from utils.timing           import timed

    pdf_p   = PDFParser(ocr_enabled=st.session_state.ocr_enabled,
                        ocr_engine=st.session_state.ocr_engine)
    docx_p  = DOCXParser()
    cleaner = TextCleaner()

    user_id = st.session_state.get("user_id")

    def _parse_one(f):
        path = save_uploaded_file(f, "sources", user_id=user_id)
        ext  = os.path.splitext(path)[1].lower()
        with timed(f"parse[{os.path.basename(path)}]"):
            if ext == ".pdf":           doc = pdf_p.parse(path)
            elif ext in (".docx",".doc"): doc = docx_p.parse(path)
            else:
                doc = {"source": path, "metadata": {},
                       "pages": [{"page_number": 1,
                                   "text": open(path, encoding="utf-8", errors="ignore").read(),
                                   "tables": [], "source": os.path.basename(path)}]}
            doc["pages"] = [cleaner.clean(p) for p in doc["pages"]]
        return path, doc

    with timed(f"parse_all[{len(st.session_state.source_files)} files]"):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            results = list(ex.map(_parse_one, st.session_state.source_files))
    return [r[0] for r in results], [r[1] for r in results]


def _auto_classify(raw_docs):
    try:
        from ingestion.document_classifier import classify_document
        c = classify_document(raw_docs[0], use_llm=False)
        st.session_state.chunking_method = c["chunking_method"]
        st.session_state.chunk_size      = c["chunk_size"]
        st.session_state.chunk_overlap   = c["chunk_overlap"]
        return c
    except Exception as e:
        logger.warning(f"Auto-classify: {e}")


def _build_indexes(source_paths, raw_docs):
    from chunking.chunk_manager       import ChunkManager, _cosine
    from embeddings.embedding_factory import EmbeddingFactory
    from embeddings.embedding_cache   import _cache_key, load_cached, save_cache
    from indexing.hierarchical_index  import HierarchicalIndex
    from indexing.bm25_index          import BM25Index
    from utils.timing import timed, print_summary

    cm       = ChunkManager(method=st.session_state.chunking_method,
                            chunk_size=st.session_state.chunk_size,
                            chunk_overlap=st.session_state.chunk_overlap)
    embedder = EmbeddingFactory(st.session_state.embedding_model).get_embedder()
    all_chunks, cache_hits, uncached = [], 0, []
    # Chunks for EACH document, same order as source_paths/raw_docs — built
    # directly as we go (whether from cache or freshly chunked) rather than
    # reconstructed afterwards by matching chunk["source"] against a
    # filename. That string match is what used to silently break "View
    # Original Page": chunk["source"] is stamped with the temp upload's
    # filename at the time it was FIRST chunked, which includes a random
    # per-upload prefix (see save_uploaded_file) — so on any cache hit
    # (same file content, re-processed or re-uploaded) the stamped source
    # would carry a different, older prefix than the current upload and
    # never match, and save_document() would silently be skipped for that
    # document, leaving no permanent PDF copy to view.
    chunks_per_doc = [None] * len(source_paths)
    doc_positions   = {}   # path -> index, so cache hits can be placed back correctly
    for i, path in enumerate(source_paths):
        doc_positions[path] = i

    for doc, path in zip(raw_docs, source_paths):
        key = _cache_key(path, st.session_state.embedding_model,
                         st.session_state.chunk_size, st.session_state.chunk_overlap,
                         st.session_state.chunking_method)
        hit = load_cached(key)
        if hit:
            all_chunks.extend(hit[0]); cache_hits += 1
            chunks_per_doc[doc_positions[path]] = hit[0]
        else:
            uncached.append((doc, path, key))

    if uncached:
        # Chunk each uncached doc ONCE (previously this ran chunk_document twice
        # per doc — once to gather texts, once again to attach embeddings —
        # doubling chunking time for no reason).
        #
        # Chunking across MULTIPLE docs now also runs in parallel (was a plain
        # sequential list comprehension before — with several source files doc 2
        # didn't even start chunking until doc 1's chunker fully finished).
        # ChunkManager.chunk_document() opens its own thread pool per call, so
        # outer workers are capped low (2) to avoid over-subscribing CPU with
        # nested pools while still overlapping the work.
        with timed(f"chunk[{len(uncached)} docs]"):
            if len(uncached) > 1:
                with concurrent.futures.ThreadPoolExecutor(
                        max_workers=min(2, len(uncached))) as ex:
                    chunked = list(ex.map(lambda item: cm.chunk_document(item[0]), uncached))
                doc_chunks = [(path, key, chunks)
                              for (doc, path, key), chunks in zip(uncached, chunked)]
            else:
                doc_chunks = [(path, key, cm.chunk_document(doc)) for doc, path, key in uncached]
        all_texts = [c["text"] for _, _, chunks in doc_chunks for c in chunks]
        all_vecs  = embedder.embed_batch(all_texts)   # timed internally in local_embeddings.py
        vc = 0
        with timed("attach_embeddings+cache_save"):
            for path, key, chunks in doc_chunks:
                n = len(chunks)
                vecs = all_vecs[vc:vc+n]; vc += n
                prev_v = None
                for c, v in zip(chunks, vecs):
                    c["embedding"]   = v
                    c["cosine_prev"] = round(_cosine(prev_v, v), 4)
                    prev_v = v
                save_cache(key, chunks, vecs)
                all_chunks.extend(chunks)
                chunks_per_doc[doc_positions[path]] = chunks

    with timed("faiss.build"):
        h = HierarchicalIndex(); h.build(all_chunks, raw_docs)
    with timed("bm25.build"):
        b = BM25Index(); b.build(all_chunks)

    print_summary()
    _persist_for_current_user(source_paths, chunks_per_doc)
    return embedder, h, b, all_chunks, cache_hits


def _persist_for_current_user(source_paths, chunks_per_doc):
    """Save each uploaded document individually into the logged-in user's
    document library (disk) so it can be reused in ANY chat later without
    re-uploading or re-embedding. Stashes the new document IDs in
    session_state for the caller to pick up (keeps _build_indexes' return
    signature unchanged for its other caller, the batch pipeline).

    chunks_per_doc is positionally aligned with source_paths (see
    _build_indexes) — each document's own chunks are passed in directly,
    not re-derived by matching a filename string against chunk metadata."""
    user_id = st.session_state.get("user_id")
    st.session_state["_last_persisted_doc_ids"] = []
    if not user_id or not chunks_per_doc:
        return
    try:
        import hashlib
        from db.user_store import save_document, UploadLimitExceeded
        doc_ids = []
        # Original, human-readable filenames the user actually uploaded —
        # positionally aligned with source_paths/chunks_per_doc — so the
        # library always shows the real document name, never the temp
        # upload path's randomised prefix.
        original_names = [
            getattr(f, "name", None) or os.path.basename(p)
            for f, p in zip(st.session_state.get("source_files", []), source_paths)
        ]
        for path, chunks_for_doc, orig_name in zip(source_paths, chunks_per_doc, original_names):
            if not chunks_for_doc:
                continue
            # Overwrite the temp upload's randomised-prefix filename with the
            # real, human-readable name BEFORE saving, so it's baked into
            # what's persisted to disk (and therefore correct on every
            # future load too, not just this run's in-memory chunks).
            for c in chunks_for_doc:
                c["source"] = orig_name
            try:
                with open(path, "rb") as f:
                    fhash = hashlib.sha256(f.read()).hexdigest()[:16]
            except OSError:
                fhash = None
            try:
                doc_id = save_document(
                    user_id, orig_name, chunks_for_doc, fhash,
                    st.session_state.chunking_method, st.session_state.chunk_size,
                    st.session_state.chunk_overlap, st.session_state.embedding_model,
                    source_file_path=path)
                doc_ids.append(doc_id)
                # Also stamp the real doc_id directly onto these chunks —
                # same objects already indexed by FAISS/BM25, so this
                # updates them everywhere they're used, retrieval included.
                # Without this, the "View Original Page" citation UI had no
                # doc_id to look up at all for a document just processed in
                # THIS run, and fell back to matching chunk["source"]
                # against the library's filename — which (before the fix
                # above) could never match the temp path's random prefix.
                for c in chunks_for_doc:
                    c["_doc_id"] = doc_id
            except UploadLimitExceeded as e:
                st.warning(str(e))
                break
        st.session_state["_last_persisted_doc_ids"] = doc_ids
    except Exception as e:
        logger.warning(f"Per-user persistence skipped: {e}")


def _build_and_store_indexes():
    try:
        sp, rd = _parse_source_docs()
        _build_indexes(sp, rd)  # builds + saves each doc into the user's library
        doc_ids = st.session_state.pop("_last_persisted_doc_ids", [])
        user_id = st.session_state.get("user_id")
        if user_id and doc_ids:
            from db.user_store import create_chat_session
            if "chat_session_id" not in st.session_state:
                st.session_state.chat_session_id = create_chat_session(user_id)
            from ui.chat_ui import apply_doc_selection
            apply_doc_selection(user_id, st.session_state.chat_session_id, doc_ids)
        st.session_state.indexes_built = True
        try:
            from ingestion.document_summarizer import summarize_document
            st.session_state.doc_summaries = [summarize_document(d) for d in rd]
        except Exception: pass
    except Exception as e:
        from utils.safe_error import show_safe_error
        show_safe_error("Couldn't build the search index for these documents.", exc=e)


# ── Main ─────────────────────────────────────────────────────────────────────────
def main():
    # Admin dashboard, reachable at ?admin=1 on THIS SAME running app — no need
    # to separately run `streamlit run admin.py`. This is still the single-code
    # gate from config.settings.ADMIN_CODE (RAS_ADMIN_CODE secret/env var), it's
    # just now reachable without a second process/port. admin.py is untouched
    # and still works too, if you'd rather run it fully isolated on its own port.
    if st.query_params.get("admin") is not None:
        from config.settings import ADMIN_CODE
        from ui.admin_ui import render_admin_page
        if ADMIN_CODE == "admin-changeme":
            st.error(
                "**Admin dashboard is disabled.** `RAS_ADMIN_CODE` is still set to the "
                "default value (`admin-changeme`). Set a real code first:\n\n"
                "- Locally: add `RAS_ADMIN_CODE = \"your-password\"` to `.streamlit/secrets.toml`\n"
                "- Or set the `RAS_ADMIN_CODE` environment variable\n\n"
                "This check exists so the admin dashboard can never accidentally ship "
                "reachable with a publicly-known password."
            )
            st.stop()
        render_admin_page()
        return

    from auth.auth import require_login
    require_login()   # renders login form + st.stop()s until authenticated (or forces a password change)

    _init()

    if st.session_state.pop("just_logged_in", False):
        # Deliberately do NOT auto-load a previous chat here — every login
        # starts a brand-new chat. Past chats are one click away in the
        # sidebar (see ui/chat_ui.py), and picking one restores its full
        # history + document selection.
        st.session_state.app_mode = "chat"
        st.session_state.wizard_phase = 3

    if st.session_state.get("semantic_cache") is None:
        from retrieval.semantic_cache import SemanticCache
        st.session_state.semantic_cache = SemanticCache()

    _topbar()
    _wizard_bar()

    phase = st.session_state.wizard_phase
    if   phase == 1: _phase1()
    elif phase == 2: _phase2()
    elif phase == 3: _phase3()


if __name__ == "__main__":
    main()