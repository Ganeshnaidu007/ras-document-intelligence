"""chunking/chunk_manager.py — Dispatches to chunking strategy; parallel across doc segments."""
import uuid, re
import concurrent.futures
import numpy as np
from typing import List, Dict, Any
from utils.logger import get_logger
from utils.timing import timed
logger = get_logger(__name__)


def _cosine(a, b) -> float:
    if a is None or b is None: return 0.0
    va, vb = np.array(a, dtype="float32"), np.array(b, dtype="float32")
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    return float(np.dot(va, vb) / (na * nb + 1e-9)) if na and nb else 0.0


class ChunkManager:
    # How many parallel segments to aim for, even for a single-page document.
    MAX_WORKERS = 4

    def __init__(self, method: str = "Semantic + Recursive Hybrid",
                 chunk_size: int = 500, chunk_overlap: int = 50):
        self.method        = method
        self.chunk_size    = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        source   = doc.get("source", "unknown")
        metadata = doc.get("metadata", {})
        pages    = [p for p in doc.get("pages", []) if p.get("text", "").strip()]
        if not pages:
            return []

        # Build parallel work units. If the doc already has >= MAX_WORKERS
        # pages, each page is its own unit. If it's a single page (or just a
        # couple), that page's text is itself split into up to MAX_WORKERS
        # paragraph-aligned segments so a ONE-page or ONE-doc upload still
        # gets chunked in parallel, not just multi-page docs.
        work_items = self._make_work_items(pages)

        results = [None] * len(work_items)
        with timed(f"chunk_document[{source}, {len(work_items)} parallel parts]"):
            workers = min(self.MAX_WORKERS, len(work_items)) or 1
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
                futs = {ex.submit(self._run, text): i for i, (_, text) in enumerate(work_items)}
                for fut in concurrent.futures.as_completed(futs):
                    i = futs[fut]
                    try:
                        results[i] = fut.result()
                    except Exception as e:
                        logger.error(f"Chunk segment {i} failed: {e}")
                        results[i] = []

        all_chunks, idx = [], 0
        for (pnum, _), raw_chunks in zip(work_items, results):
            for ct in (raw_chunks or []):
                if not ct.strip():
                    continue
                all_chunks.append({
                    "chunk_id":        str(uuid.uuid4())[:8],
                    "text":            ct.strip(),
                    "source":          source,
                    "page_number":     pnum,
                    "chunk_index":     idx,
                    "author":          metadata.get("author", ""),
                    "parent_section":  "",
                    "language":        "",
                    "semantic_tags":   [],
                    "token_count":     len(ct.split()),
                    # Real embedding + cosine_prev are attached ONCE, later,
                    # right after the pipeline's single batched embed_batch()
                    # call (see app.py _build_indexes). Doing it here too was
                    # a wasted duplicate model call — its output was always
                    # overwritten before being used.
                    "embedding":       None,
                    "cosine_prev":     0.0,
                })
                idx += 1
        logger.info(f"{len(all_chunks)} chunks from {source} ({len(work_items)} parallel parts)")
        return all_chunks

    def _make_work_items(self, pages):
        """Return list of (page_number, text) work units, parallelizable
        even when the document is a single page."""
        if len(pages) >= self.MAX_WORKERS:
            return [(p.get("page_number", 0), p.get("text", "").strip()) for p in pages]

        items = []
        parts_per_page = max(1, self.MAX_WORKERS // len(pages))
        for p in pages:
            pnum = p.get("page_number", 0)
            text = p.get("text", "").strip()
            for seg in self._split_into_segments(text, parts_per_page):
                items.append((pnum, seg))
        return items

    def _split_into_segments(self, text: str, n_parts: int) -> List[str]:
        """Split text into ~n_parts pieces on paragraph boundaries (never
        mid-sentence), so each piece can be chunked independently and the
        results simply concatenate back in order."""
        if n_parts <= 1 or not text:
            return [text]
        paras = [p for p in re.split(r"\n{2,}", text) if p.strip()]
        if len(paras) < n_parts:
            # Not enough natural breakpoints (e.g. one huge paragraph) —
            # fall back to a single segment rather than cutting mid-sentence.
            return [text]
        target = sum(len(p.split()) for p in paras) / n_parts
        segments, cur, cur_w = [], [], 0
        for p in paras:
            cur.append(p); cur_w += len(p.split())
            if cur_w >= target and len(segments) < n_parts - 1:
                segments.append("\n\n".join(cur)); cur, cur_w = [], 0
        if cur:
            segments.append("\n\n".join(cur))
        return segments

    def _run(self, text: str) -> List[str]:
        m = self.method.lower()
        if "semantic" in m and "recursive" in m:
            from chunking.recursive_chunker import RecursiveChunker
            from chunking.semantic_chunker  import SemanticChunker
            coarse = RecursiveChunker(self.chunk_size, self.chunk_overlap).chunk(text)
            fine = []
            for c in coarse:
                fine.extend(SemanticChunker(self.chunk_size).chunk(c))
            return fine
        if "semantic"  in m: from chunking.semantic_chunker  import SemanticChunker;  return SemanticChunker(self.chunk_size).chunk(text)
        if "recursive" in m: from chunking.recursive_chunker import RecursiveChunker; return RecursiveChunker(self.chunk_size, self.chunk_overlap).chunk(text)
        if "sliding"   in m: from chunking.sliding_window    import SlidingWindowChunker; return SlidingWindowChunker(self.chunk_size, self.chunk_size - self.chunk_overlap).chunk(text)
        if "paragraph" in m: return [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        if "sentence"  in m: return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        from chunking.fixed_chunker import FixedChunker
        return FixedChunker(self.chunk_size, self.chunk_overlap).chunk(text)