"""retrieval/reranker.py — Fast cached reranker."""
import os
import utils.model_cache  # noqa: F401 — sets HF_HOME etc. before any model import
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from typing import List, Dict, Any
from utils.logger import get_logger
from utils.device import get_device
from utils.timing import timed
logger = get_logger(__name__)

# Smaller, faster model — 22MB vs 1.1GB, still very accurate
MODEL_MAP = {
    "bge reranker":           "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "cross encoder ms-marco": "cross-encoder/ms-marco-MiniLM-L-6-v2",
}

_RERANKER_CACHE = {}  # module-level — loaded once per process


def _get_cross_encoder(model_id: str):
    if model_id not in _RERANKER_CACHE:
        from sentence_transformers import CrossEncoder
        device = get_device()
        logger.info(f"Loading reranker (once): {model_id} on device={device}")
        _RERANKER_CACHE[model_id] = CrossEncoder(model_id, device=device)
    return _RERANKER_CACHE[model_id]


class Reranker:
    def __init__(self, enabled: bool = True, model: str = "BGE Reranker"):
        self.enabled    = enabled
        self.model_name = model

    def rerank(self, query: str, chunks: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.enabled or not chunks:
            return chunks[:top_k]
        if "cohere" in self.model_name.lower():
            return self._cohere(query, chunks, top_k)
        return self._cross_enc(query, chunks, top_k)

    def _cross_enc(self, query, chunks, top_k):
        model_id = MODEL_MAP.get(self.model_name.lower(), "cross-encoder/ms-marco-MiniLM-L-6-v2")
        try:
            model = _get_cross_encoder(model_id)
            with timed(f"rerank[{len(chunks)} chunks]"):
                scores = model.predict([(query, c.get("text", "")) for c in chunks])
            for c, sc in zip(chunks, scores):
                c["rerank_score"] = float(sc)
            return sorted(chunks, key=lambda x: x.get("rerank_score", 0.0), reverse=True)[:top_k]
        except Exception as e:
            logger.error(f"Rerank error: {e}"); return chunks[:top_k]

    def _cohere(self, query, chunks, top_k):
        try:
            import cohere
            from config.settings import COHERE_API_KEY
            resp = cohere.ClientV2(api_key=COHERE_API_KEY).rerank(
                query=query,
                documents=[c.get("text", "") for c in chunks],
                top_n=top_k, model="rerank-english-v3.0")
            return [dict({**chunks[r.index], "rerank_score": r.relevance_score})
                    for r in resp.results]
        except Exception as e:
            logger.error(f"Cohere rerank: {e}"); return chunks[:top_k]