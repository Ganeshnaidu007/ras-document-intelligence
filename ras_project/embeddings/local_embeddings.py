"""embeddings/local_embeddings.py — Local sentence-transformers embedder (loads once)."""
import utils.model_cache  # noqa: F401 — sets HF_HOME etc. before any model import (single source of truth)

import streamlit as st
from typing import List
from utils.logger import get_logger
from utils.device import get_device
from utils.timing import timed
logger = get_logger(__name__)

MODEL_MAP = {
    "all-minilm-l6-v2": "all-MiniLM-L6-v2",
    "bge-small-en":      "BAAI/bge-small-en",
    "instructor-xl":     "hkunlp/instructor-xl",
}

@st.cache_resource(show_spinner="Loading embedding model…")
def _load_model(model_name: str):
    from sentence_transformers import SentenceTransformer
    device = get_device()
    logger.info(f"Loading model (once): {model_name} on device={device}")
    return SentenceTransformer(model_name, device=device)

class LocalEmbedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = MODEL_MAP.get(model_name.lower(), model_name)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts: return []
        try:
            with timed(f"embed.batch[{len(texts)} chunks]"):
                return _load_model(self.model_name).encode(
                    texts, show_progress_bar=False, convert_to_numpy=True
                ).tolist()
        except Exception as e:
            logger.error(f"Embed error: {e}")
            return [[0.0] * 384] * len(texts)

    def embed_single(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]