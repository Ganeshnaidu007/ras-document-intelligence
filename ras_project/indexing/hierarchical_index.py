"""indexing/hierarchical_index.py — Hierarchical FAISS + page-aware index."""
from typing import List, Dict, Any
from utils.logger import get_logger
logger = get_logger(__name__)


class HierarchicalIndex:
    def __init__(self):
        self._chunks: List[Dict[str, Any]] = []
        self._faiss  = None
        self._dim    = 0
        self._page_map: Dict[str, List[int]] = {}

    def build(self, chunks: List[Dict[str, Any]], docs=None):
        self._chunks = chunks
        valid = [c for c in chunks if c.get("embedding")]
        if not valid:
            logger.warning("No embedded chunks for HierarchicalIndex."); return
        self._dim   = len(valid[0]["embedding"])
        self._faiss = self._build_faiss(valid)
        self._build_page_map(chunks)
        logger.info(f"HierarchicalIndex: {len(valid)} vectors dim={self._dim}")

    def _build_faiss(self, chunks):
        try:
            import faiss, numpy as np
            vecs = np.array([c["embedding"] for c in chunks], dtype="float32")
            faiss.normalize_L2(vecs)
            idx = faiss.IndexFlatIP(self._dim); idx.add(vecs); return idx
        except ImportError:
            logger.warning("FAISS not installed — using brute-force search."); return None
        except Exception as e:
            logger.error(f"FAISS build: {e}"); return None

    def _build_page_map(self, chunks):
        self._page_map = {}
        for i, c in enumerate(chunks):
            key = f"{c.get('source','')}:{c.get('page_number',0)}"
            self._page_map.setdefault(key,[]).append(i)

    def search(self, q_emb: List[float], top_k: int = 20) -> List[Dict[str, Any]]:
        if self._faiss is None:
            return self._brute(q_emb, top_k)
        try:
            import faiss, numpy as np
            q = np.array([q_emb], dtype="float32"); faiss.normalize_L2(q)
            scores, indices = self._faiss.search(q, min(top_k, len(self._chunks)))
            out = []
            for sc, idx in zip(scores[0], indices[0]):
                if idx < 0: continue
                c = dict(self._chunks[idx]); c["dense_score"] = float(sc); out.append(c)
            return out
        except Exception as e:
            logger.error(f"FAISS search: {e}"); return []

    def get_chunks_for_page(self, source, page_number):
        return [self._chunks[i] for i in self._page_map.get(f"{source}:{page_number}", [])]

    def _brute(self, q_emb, top_k):
        def cos(a, b):
            d = sum(x*y for x,y in zip(a,b))
            na = sum(x*x for x in a)**0.5; nb = sum(x*x for x in b)**0.5
            return d/(na*nb+1e-9)
        results = []
        for c in self._chunks:
            emb = c.get("embedding")
            if emb:
                cc = dict(c); cc["dense_score"] = cos(q_emb, emb); results.append(cc)
        results.sort(key=lambda x: x["dense_score"], reverse=True)
        return results[:top_k]
