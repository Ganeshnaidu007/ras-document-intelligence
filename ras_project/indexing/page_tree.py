"""indexing/page_tree.py — Hierarchical Document → Page → Section → Chunk tree."""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ChunkNode:
    chunk_id:   str
    text:       str
    token_count: int
    embedding:  Optional[List[float]] = None
    metadata:   Dict[str, Any] = field(default_factory=dict)


@dataclass
class SectionNode:
    title:       str
    page_number: int
    source:      str
    chunks:      List[ChunkNode] = field(default_factory=list)


@dataclass
class PageNode:
    page_number: int
    source:      str
    sections:    List[SectionNode] = field(default_factory=list)
    page_metadata: Dict[str, Any]  = field(default_factory=dict)

    def all_chunks(self): return [c for s in self.sections for c in s.chunks]


@dataclass
class DocumentNode:
    source:   str
    metadata: Dict[str, Any] = field(default_factory=dict)
    pages:    List[PageNode]  = field(default_factory=list)

    def all_chunks(self): return [c for p in self.pages for c in p.all_chunks()]

    def get_page(self, pnum: int) -> Optional[PageNode]:
        return next((p for p in self.pages if p.page_number == pnum), None)


class PageIndexTree:
    def __init__(self):
        self.documents: Dict[str, DocumentNode] = {}

    def build_from_chunks(self, chunks: List[Dict[str, Any]], docs=None):
        by_src: Dict[str, List[Dict]] = {}
        for c in chunks: by_src.setdefault(c.get("source","unknown"),[]).append(c)
        for src, src_chunks in by_src.items():
            doc_meta = {}
            if docs:
                for d in docs:
                    if src in d.get("source",""):
                        doc_meta = d.get("metadata",{}); break
            doc_node = DocumentNode(source=src, metadata=doc_meta)
            by_page: Dict[int, List[Dict]] = {}
            for c in src_chunks: by_page.setdefault(c.get("page_number",1),[]).append(c)
            for pn, pchunks in sorted(by_page.items()):
                page_node = PageNode(page_number=pn, source=src)
                section   = SectionNode(title="", page_number=pn, source=src)
                for c in pchunks:
                    section.chunks.append(ChunkNode(
                        chunk_id=c.get("chunk_id",""), text=c.get("text",""),
                        token_count=c.get("token_count",0), embedding=c.get("embedding"),
                        metadata={k:v for k,v in c.items() if k not in ("text","embedding")}))
                page_node.sections.append(section)
                doc_node.pages.append(page_node)
            self.documents[src] = doc_node
