"""ui/settings_ui.py — Configuration widgets, professional style."""
import streamlit as st
from config.settings import (
    CHUNKING_METHODS, CHUNK_SIZE_OPTIONS, CHUNK_OVERLAP_OPTIONS,
    ALL_EMBEDDING_MODELS, RETRIEVAL_STRATEGIES, RERANKING_MODELS,
    OCR_ENGINES, SUPPORTED_LANGUAGES, OUTPUT_FORMATS,
)


def render_chunking_settings():
    st.markdown('<span class="ras-label">Chunking</span>', unsafe_allow_html=True)
    st.session_state.chunking_method = st.selectbox(
        "Method", CHUNKING_METHODS,
        index=CHUNKING_METHODS.index(st.session_state.get("chunking_method", CHUNKING_METHODS[0])),
        label_visibility="collapsed",
    )
    col_cs, col_ov = st.columns(2)
    with col_cs:
        if st.checkbox("Custom size", key="cb_cs"):
            st.session_state.chunk_size = st.number_input(
                "Chunk size (tokens)", 50, 4000,
                st.session_state.get("chunk_size", 500), 50,
                label_visibility="collapsed")
        else:
            _cs = st.session_state.get("chunk_size", 500)
            if _cs not in CHUNK_SIZE_OPTIONS:
                _cs = min(CHUNK_SIZE_OPTIONS, key=lambda x: abs(x - _cs))
            st.session_state.chunk_size = st.select_slider(
                "Chunk size", CHUNK_SIZE_OPTIONS, _cs)
    with col_ov:
        if st.checkbox("Custom overlap", key="cb_ov"):
            st.session_state.chunk_overlap = st.number_input(
                "Overlap (tokens)", 0, 500,
                st.session_state.get("chunk_overlap", 50), 10,
                label_visibility="collapsed")
        else:
            _co = st.session_state.get("chunk_overlap", 50)
            if _co not in CHUNK_OVERLAP_OPTIONS:
                _co = min(CHUNK_OVERLAP_OPTIONS, key=lambda x: abs(x - _co))
            st.session_state.chunk_overlap = st.select_slider(
                "Overlap", CHUNK_OVERLAP_OPTIONS, _co)
    st.session_state.language = st.selectbox(
        "Language", SUPPORTED_LANGUAGES,
        index=SUPPORTED_LANGUAGES.index(st.session_state.get("language", "English")))


def render_embedding_settings():
    st.markdown('<span class="ras-label">Embedding</span>', unsafe_allow_html=True)
    st.session_state.embedding_model = st.selectbox(
        "Model", ALL_EMBEDDING_MODELS,
        index=ALL_EMBEDDING_MODELS.index(
            st.session_state.get("embedding_model", "all-MiniLM-L6-v2")),
        label_visibility="collapsed",
    )
    m = st.session_state.embedding_model
    if m.startswith("OpenAI"):
        st.text_input("OpenAI API Key", type="password", key="openai_key",
                      placeholder="sk-...")
    elif m.startswith("Gemini"):
        st.text_input("Google API Key", type="password", key="google_key",
                      placeholder="AIza...")
    elif m.startswith("Cohere"):
        st.text_input("Cohere API Key", type="password", key="cohere_key",
                      placeholder="...")


def render_retrieval_settings():
    st.markdown('<span class="ras-label">Retrieval</span>', unsafe_allow_html=True)
    st.session_state.retrieval_strategy = st.selectbox(
        "Strategy", RETRIEVAL_STRATEGIES,
        index=RETRIEVAL_STRATEGIES.index(
            st.session_state.get("retrieval_strategy", "Hybrid Retrieval")),
        label_visibility="collapsed",
    )
    col_r, col_m = st.columns(2)
    with col_r:
        st.session_state.reranking_enabled = st.toggle(
            "Re-ranking", value=st.session_state.get("reranking_enabled", True))
    with col_m:
        st.session_state.multi_query_enabled = st.toggle(
            "Multi-query", value=st.session_state.get("multi_query_enabled", True),
            help="Expand each question into multiple retrieval queries for better recall.")
    if st.session_state.reranking_enabled:
        st.session_state.reranking_model = st.selectbox(
            "Re-ranking model", RERANKING_MODELS,
            index=RERANKING_MODELS.index(
                st.session_state.get("reranking_model", "BGE Reranker")))


def render_ocr_settings():
    st.markdown('<span class="ras-label">OCR</span>', unsafe_allow_html=True)
    st.session_state.ocr_enabled = st.toggle(
        "Enable OCR", value=st.session_state.get("ocr_enabled", True))
    if st.session_state.ocr_enabled:
        st.session_state.ocr_engine = st.selectbox(
            "Engine", OCR_ENGINES,
            index=OCR_ENGINES.index(st.session_state.get("ocr_engine", "EasyOCR")))
        st.caption("EasyOCR and PaddleOCR support Hindi and Telugu.")


def render_output_settings():
    st.markdown('<span class="ras-label">Output</span>', unsafe_allow_html=True)
    st.markdown('<div class="helper-note">Changes are saved automatically.</div>', unsafe_allow_html=True)
    st.session_state.output_format = st.selectbox(
        "Format", OUTPUT_FORMATS,
        index=OUTPUT_FORMATS.index(
            st.session_state.get("output_format", "PDF")))