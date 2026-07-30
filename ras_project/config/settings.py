"""config/settings.py — Global settings and defaults."""
import os
import streamlit as st


def _secret(key: str, fallback: str = "") -> str:
    try:
        return st.secrets.get(key, os.getenv(key, fallback))
    except Exception:
        return os.getenv(key, fallback)


BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR   = os.path.join(BASE_DIR, "temp")
CACHE_DIR  = os.path.join(BASE_DIR, "cache")
OUTPUT_DIR = os.path.join(BASE_DIR, "generated_outputs")
for _d in (TEMP_DIR, CACHE_DIR, OUTPUT_DIR):
    os.makedirs(_d, exist_ok=True)

# ── API Keys ──────────────────────────────────────────────────────────────────
OPENAI_API_KEY     = _secret("OPENAI_API_KEY")
GOOGLE_API_KEY     = _secret("GOOGLE_API_KEY")
GROQ_API_KEY       = _secret("GROQ_API_KEY")
OPENROUTER_API_KEY = _secret("OPENROUTER_API_KEY")
JINA_API_KEY       = _secret("JINA_API_KEY")
COHERE_API_KEY     = _secret("COHERE_API_KEY")
SERP_API_KEY       = _secret("SERP_API_KEY")

# ── Auth (real accounts: username + password) ───────────────────────────────
# Each person signs up with their own username/password — see db/user_store.py
# for the hashing (PBKDF2-SHA256, per-user salt, no plaintext ever stored).
MIN_PASSWORD_LENGTH = 8

# Separate credentials for the admin dashboard — a normal user account can
# never reach it just by logging in; these are independent secrets from the
# per-user accounts above. Both must be set (or left at their obvious
# defaults, which the admin app refuses to run with).
ADMIN_USERNAME = _secret("RAS_ADMIN_USERNAME", "admin")
ADMIN_CODE     = _secret("RAS_ADMIN_CODE", "admin-changeme")

# ── Multi-user storage ───────────────────────────────────────────────────────
# IMPORTANT: this is real, non-regenerable user data (documents, embeddings,
# chat history) — deliberately kept OUT of CACHE_DIR, which is for things
# that are safe to delete and will just re-download/re-compute (models, the
# content-addressed embedding cache). Losing DATA_DIR loses actual user work,
# so back this up / mount it on persistent storage when you deploy.
DATA_DIR         = os.path.join(BASE_DIR, "data")
USER_DB_PATH     = os.path.join(DATA_DIR, "ras_users.db")
USER_DOCS_DIR    = os.path.join(DATA_DIR, "user_documents")   # one chunk+embedding file PER document
os.makedirs(USER_DOCS_DIR, exist_ok=True)
# Max number of chat sessions' document-sets held in server RAM at once.
# Beyond this, the least-recently-active one is evicted from memory (data is
# safe on disk, reloads in ~1s next time it's active). This is what keeps
# RAM bounded no matter how many people have used the app in total — only
# the CURRENTLY active chats cost memory.
MAX_HOT_USERS = int(_secret("RAS_MAX_HOT_USERS", "8") or 8)

# Max number of NEW files any one person can upload/process per rolling 24h.
# Stops one person from eating all the server's disk/compute; adjust via
# the RAS_MAX_UPLOADS_PER_DAY secret/env var if you need a different cap.
MAX_UPLOADS_PER_DAY = int(_secret("RAS_MAX_UPLOADS_PER_DAY", "5") or 5)


# ── LLM ───────────────────────────────────────────────────────────────────────
LLM_MAX_TOKENS  = 2000
LLM_TEMPERATURE = 0.2

# Groq models — ONLY live models as of June 2026.
# mixtral-8x7b-32768 and gemma2-9b-it are DECOMMISSIONED — never add them back.
# llama-3.3-70b-versatile = best quality but hits TPM fast on free tier.
# llama-3.1-8b-instant    = fastest, lowest token cost — use as primary fallback.
# llama3-70b-8192         = stable alias, good for reasoning steps.
GROQ_MODELS = [
    "llama-3.1-8b-instant",       # fastest, lowest TPM cost → use first
    "llama-3.3-70b-versatile",    # higher quality, use when 8b fails
    "llama3-70b-8192",            # stable fallback alias
]

# OpenRouter models
OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct",
    "google/gemini-2.0-flash-001",
    "mistralai/mistral-7b-instruct",
    "anthropic/claude-3-haiku",
]

# Gemini models — ordered cheapest/fastest first to preserve free quota.
# gemini-2.0-flash-lite  = cheapest, hits quota last
# gemini-2.5-flash       = best reasoning, use as fallback
# gemini-2.0-flash       = middle ground (hits free quota quickly)
GEMINI_MODELS = [
    "gemini-2.0-flash-lite",   # cheapest → try first
    "gemini-2.5-flash",        # best quality fallback
    "gemini-2.0-flash",        # last resort (quota exhausts fast)
]

# ── Rate-limit back-off ───────────────────────────────────────────────────────
# How long to wait (seconds) before trying the next model after a 429.
# The groq client retries internally — this controls cross-model delay.
RATE_LIMIT_PAUSE = 0   # 0 = rely on groq client's built-in retry; set >0 to add extra delay

# ── Chunking ──────────────────────────────────────────────────────────────────
CHUNKING_METHODS = [
    "Semantic + Recursive Hybrid", "Fixed Chunking", "Recursive Chunking",
    "Semantic Chunking", "Sliding Window Chunking", "Paragraph Chunking", "Sentence Chunking",
]
CHUNK_SIZE_OPTIONS    = [100, 200, 300, 500, 800, 1000]
CHUNK_OVERLAP_OPTIONS = [10, 20, 50, 100, 200]

# ── Embeddings ────────────────────────────────────────────────────────────────
LOCAL_EMBEDDING_MODELS = ["all-MiniLM-L6-v2", "bge-small-en", "multilingual-e5",
                           "instructor-xl", "bge-m3", "LaBSE"]
CLOUD_EMBEDDING_MODELS = [
    "OpenAI text-embedding-3-small",
    "Gemini text-embedding-004",
    "Jina embeddings-v3",
    "Cohere Embed",
]
ALL_EMBEDDING_MODELS = LOCAL_EMBEDDING_MODELS + CLOUD_EMBEDDING_MODELS

# ── Retrieval ─────────────────────────────────────────────────────────────────
RETRIEVAL_STRATEGIES = ["Hybrid Retrieval", "Dense Retrieval", "BM25 Sparse Retrieval"]
RETRIEVAL_TOP_K      = 20
RERANK_TOP_K         = 5
RERANKING_MODELS     = ["BGE Reranker", "Cross Encoder ms-marco", "Cohere Rerank"]

# ── Jina ──────────────────────────────────────────────────────────────────────
JINA_EMBED_URL   = "https://api.jina.ai/v1/embeddings"
JINA_READER_URL  = "https://r.jina.ai/"
JINA_EMBED_MODEL = "jina-embeddings-v3"

# ── OCR ───────────────────────────────────────────────────────────────────────
OCR_ENGINES         = ["EasyOCR", "PaddleOCR", "Tesseract"]
SUPPORTED_LANGUAGES = ["English", "Hindi", "Telugu", "Mixed Language"]

# ── Output ────────────────────────────────────────────────────────────────────
OUTPUT_FORMATS = ["PDF", "DOCX", "TXT", "JSON"]

# ── Real-time search ──────────────────────────────────────────────────────────
SERP_API_URL = "https://serpapi.com/search"
SERP_ENGINE  = "google"

# ── File limits ───────────────────────────────────────────────────────────────
SUPPORTED_SOURCE_TYPES   = ["pdf", "docx", "doc", "txt"]
SUPPORTED_QUESTION_TYPES = ["pdf", "docx", "doc", "txt"]
MAX_FILE_SIZE_MB         = 100

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_SETTINGS = {
    "chunking_method":     "Semantic + Recursive Hybrid",
    "chunk_size":          500,
    "chunk_overlap":       50,
    "embedding_model":     "all-MiniLM-L6-v2",
    "retrieval_strategy":  "Hybrid Retrieval",
    "reranking_enabled":   True,
    "reranking_model":     "BGE Reranker",
    "ocr_enabled":         True,
    "ocr_engine":          "EasyOCR",
    "language":            "English",
    "output_format":       "PDF",
    "multi_query_enabled": True,
    "real_time_search":    False,
    "llm_provider":        "gemini",
    "llm_model":           "gemini-2.0-flash-lite",
}