"""retrieval/dense_retriever.py — Dense-only retrieval wrapper."""
from typing import List, Dict, Any

class DenseRetriever:
    def __init__(self, hierarchical_index, embedder):
        self.index   = hierarchical_index
        self.embedder = embedder

    def retrieve(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        return self.index.search(self.embedder.embed_single(query), top_k=top_k)
