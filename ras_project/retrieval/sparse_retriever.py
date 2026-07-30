"""retrieval/sparse_retriever.py — BM25 sparse-only retrieval wrapper."""
from typing import List, Dict, Any

class SparseRetriever:
    def __init__(self, bm25_index):
        self.index = bm25_index

    def retrieve(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        return self.index.search(query, top_k=top_k)
