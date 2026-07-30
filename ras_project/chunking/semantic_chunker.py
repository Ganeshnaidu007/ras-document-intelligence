"""chunking/semantic_chunker.py — Semantic topic-shift chunker via sentence embeddings."""
import utils.model_cache  # noqa: F401 — sets HF_HOME etc. before any model import

import re, threading
from typing import List
from utils.logger import get_logger
logger = get_logger(__name__)

_THRESHOLD = 0.75
_MODEL_CACHE = {}  # module-level cache — survives across calls in same process
_MODEL_LOCK = threading.Lock()  # chunking now runs in parallel threads; guard first load


def _get_model():
    if "model" not in _MODEL_CACHE:
        with _MODEL_LOCK:
            if "model" not in _MODEL_CACHE:  # re-check inside lock
                try:
                    from sentence_transformers import SentenceTransformer
                    from utils.device import get_device
                    _MODEL_CACHE["model"] = SentenceTransformer("all-MiniLM-L6-v2", device=get_device())
                    logger.info("SemanticChunker: model loaded (once)")
                except Exception as e:
                    logger.warning(f"SemanticChunker model load failed: {e}")
                    _MODEL_CACHE["model"] = None
    return _MODEL_CACHE["model"]


class SemanticChunker:
    def __init__(self, max_chunk_size: int = 500, threshold: float = _THRESHOLD):
        self.max_chunk_size = max_chunk_size
        self.threshold = threshold

    def chunk(self, text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?।])\s+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) <= 1:
            return sentences
        embs = self._embed(sentences)
        if embs is None:
            return re.split(r"\n{2,}", text) or [text]
        return self._group(sentences, embs)

    def _embed(self, sentences):
        model = _get_model()
        if model is None:
            return None
        try:
            return model.encode(sentences, show_progress_bar=False)
        except Exception as e:
            logger.warning(f"Semantic embed failed: {e}")
            return None

    def _cos(self, a, b):
        import numpy as np
        na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
        return float(np.dot(a, b) / (na * nb + 1e-9)) if na and nb else 0.0

    def _group(self, sentences, embs):
        chunks, cur, cur_w = [], [sentences[0]], len(sentences[0].split())
        for i in range(1, len(sentences)):
            sim = self._cos(embs[i - 1], embs[i])
            wc  = len(sentences[i].split())
            if sim < self.threshold or cur_w + wc > self.max_chunk_size:
                chunks.append(" ".join(cur)); cur = [sentences[i]]; cur_w = wc
            else:
                cur.append(sentences[i]); cur_w += wc
        if cur:
            chunks.append(" ".join(cur))
        return chunks