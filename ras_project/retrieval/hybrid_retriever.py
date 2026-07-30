"""retrieval/hybrid_retriever.py — Hybrid retrieval with cosine similarity + RRF fusion."""
import numpy as np
from typing import List, Dict, Any
from utils.logger import get_logger
logger = get_logger(__name__)
RRF_K = 60


def _cosine(a: List[float], b: List[float]) -> float:
    va, vb = np.array(a, dtype="float32"), np.array(b, dtype="float32")
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    return float(np.dot(va, vb) / (na * nb + 1e-9)) if na and nb else 0.0


class HybridRetriever:
    def __init__(self, hierarchical_index, bm25_index, embedder, strategy: str = "Hybrid Retrieval"):
        self.h_idx    = hierarchical_index
        self.bm25     = bm25_index
        self.embedder = embedder
        self.strategy = strategy

    def retrieve(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        s = self.strategy.lower()
        if "bm25" in s or "sparse" in s:
            return self.bm25.search(query, top_k)
        if "dense" in s:
            q_emb = self._embed_query(query)
            return self._dense_with_cosine(q_emb, top_k)
        return self._hybrid(query, top_k)

    def _embed_query(self, query: str) -> List[float]:
        """Use query-specific embedding if embedder supports it (e.g. Jina)."""
        if hasattr(self.embedder, "embed_query"):
            return self.embedder.embed_query(query)
        return self.embedder.embed_single(query)

    def _dense_with_cosine(self, q_emb: List[float], top_k: int) -> List[Dict[str, Any]]:
        """Dense retrieval with explicit cosine similarity scores."""
        results = self.h_idx.search(q_emb, top_k)
        for c in results:
            if c.get("embedding"):
                c["cosine_score"] = _cosine(q_emb, c["embedding"])
            else:
                c["cosine_score"] = c.get("dense_score", 0.0)
        results.sort(key=lambda x: x["cosine_score"], reverse=True)
        return results

    def _hybrid(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        q_emb  = self._embed_query(query)
        dense  = self._dense_with_cosine(q_emb, top_k * 2)
        sparse = self.bm25.search(query, top_k * 2)

        # Build pool
        pool: Dict[str, Dict] = {}
        for c in dense + sparse:
            cid = c.get("chunk_id", c["text"][:30])
            pool[cid] = c

        # Compute explicit cosine similarity for every pooled chunk
        for cid, c in pool.items():
            if c.get("embedding") and q_emb:
                c["cosine_score"] = _cosine(q_emb, c["embedding"])
            elif "cosine_score" not in c:
                c["cosine_score"] = 0.0

        # RRF scores
        rrf: Dict[str, float] = {}
        for r, c in enumerate(dense):
            cid = c.get("chunk_id", c["text"][:30])
            rrf[cid] = rrf.get(cid, 0.0) + 1.0 / (RRF_K + r + 1)
        for r, c in enumerate(sparse):
            cid = c.get("chunk_id", c["text"][:30])
            rrf[cid] = rrf.get(cid, 0.0) + 1.0 / (RRF_K + r + 1)

        # Normalize RRF to [0,1]
        max_rrf = max(rrf.values()) if rrf else 1.0

        # Final score = 0.6 × cosine + 0.4 × normalised RRF
        for cid, c in pool.items():
            cos  = c.get("cosine_score", 0.0)
            norm = rrf.get(cid, 0.0) / (max_rrf + 1e-9)
            c["hybrid_score"] = round(0.6 * cos + 0.4 * norm, 6)

        ranked = sorted(pool.values(), key=lambda c: c["hybrid_score"], reverse=True)
        return ranked[:top_k]