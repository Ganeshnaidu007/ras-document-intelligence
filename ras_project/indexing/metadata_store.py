"""indexing/metadata_store.py — In-memory metadata store for chunk lookup and filtering."""
from typing import List, Dict, Any, Optional


class MetadataStore:
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def add(self, chunk: Dict[str, Any]):
        cid = chunk.get("chunk_id","")
        if cid:
            self._store[cid] = {k: v for k, v in chunk.items() if k != "embedding"}

    def add_batch(self, chunks):
        for c in chunks: self.add(c)

    def get(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(chunk_id)

    def filter_by_source(self, source: str) -> List[Dict]:
        return [m for m in self._store.values() if m.get("source") == source]

    def filter_by_page(self, source: str, page: int) -> List[Dict]:
        return [m for m in self._store.values()
                if m.get("source") == source and m.get("page_number") == page]

    def all_sources(self) -> List[str]:
        return list({m.get("source","") for m in self._store.values()})

    def __len__(self): return len(self._store)
