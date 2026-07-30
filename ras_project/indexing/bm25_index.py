"""indexing/bm25_index.py — BM25 sparse retrieval index."""
import re
from typing import List, Dict, Any
from utils.logger import get_logger
logger = get_logger(__name__)


class BM25Index:
    def __init__(self):
        self._chunks: List[Dict[str, Any]] = []
        self._bm25 = None
        self._tok:   List[List[str]] = []

    def build(self, chunks: List[Dict[str, Any]]):
        self._chunks = chunks
        self._tok    = [_tok(c.get("text","")) for c in chunks]
        if not self._tok:
            logger.warning("BM25 build called with 0 chunks — skipping index build.")
            return
        try:
            from rank_bm25 import BM25Okapi
            self._bm25 = BM25Okapi(self._tok)
            logger.info(f"BM25 index: {len(chunks)} chunks.")
        except ImportError:
            logger.warning("rank_bm25 not installed — using TF fallback.")

    def search(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        if not self._chunks: return []
        qt = _tok(query)
        scores = (self._bm25.get_scores(qt) if self._bm25
                  else [_tf(qt, dt) for dt in self._tok])
        ranked = sorted(zip(scores, range(len(self._chunks))), key=lambda x: x[0], reverse=True)[:top_k]
        out = []
        for score, idx in ranked:
            c = dict(self._chunks[idx]); c["bm25_score"] = float(score); out.append(c)
        return out


def _tok(text: str) -> List[str]:
    return re.findall(r"\b\w+\b", text.lower())

def _tf(qt, dt) -> float:
    if not dt: return 0.0
    freq = {}
    for t in dt: freq[t] = freq.get(t,0)+1
    return sum(freq.get(t,0) for t in qt) / len(dt)
