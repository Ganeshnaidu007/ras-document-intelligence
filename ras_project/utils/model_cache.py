"""utils/model_cache.py — Single source of truth for where downloaded models live.

Import this module FIRST (before importing sentence_transformers / transformers
/ torch anywhere) so every embedding, reranking, and chunking model — no matter
which file loads it first — writes to the SAME cache folder on disk.

Why this matters: previously this env-var setup was copy-pasted into four
different files (app.py, local_embeddings.py, semantic_chunker.py,
reranker.py) and was MISSING from multilingual_embeddings.py entirely. If
that file happened to import a model first, it would silently download to
Hugging Face's default cache (~/.cache/huggingface) instead of this app's
cache dir — so the same model could end up downloaded twice, in two
different places, depending on which module ran first. Now there is exactly
one place this is set, so a model is downloaded once and reused forever.

Uses setdefault() so it never clobbers a cache path the user has already
configured via their own environment variables.
"""
import os

# ── OpenMP duplicate-runtime fix (Windows) ──────────────────────────────────
# faiss ships its own OpenMP runtime (libomp140.x86_64.dll) and torch/MKL
# ships a different one (libiomp5md.dll). When both get loaded into the same
# process — which happens the moment this app builds a FAISS index after
# already loading a sentence-transformers embedding model — Python crashes
# with "OMP: Error #15: Initializing libomp140... but found libiomp5md...
# already initialized." KMP_DUPLICATE_LIB_OK=TRUE tells the OpenMP runtime to
# tolerate the duplicate instead of aborting. This is the officially
# documented (if inelegant) workaround; it must be set before numpy, torch,
# or faiss are imported ANYWHERE, which is why it lives here, at the very
# top of the one module every other module is required to import first.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

_CACHE_DIR = os.path.join(os.path.expanduser("~"), "hf_cache")
os.makedirs(_CACHE_DIR, exist_ok=True)

os.environ.setdefault("HF_HOME", _CACHE_DIR)
os.environ.setdefault("TRANSFORMERS_CACHE", _CACHE_DIR)
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", _CACHE_DIR)

CACHE_DIR = _CACHE_DIR
