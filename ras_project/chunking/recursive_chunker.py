"""chunking/recursive_chunker.py — Recursive separator-based chunker."""
from typing import List

class RecursiveChunker:
    SEPS = ["\n\n","\n",". ","! ","? ","; ",", "," ",""]

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap    = max(0, min(overlap, chunk_size - 1))

    def chunk(self, text: str) -> List[str]:
        return self._split(text, self.SEPS)

    def _wc(self, t):
        return len(t.split())

    def _split(self, text, seps):
        if self._wc(text) <= self.chunk_size:
            return [text] if text.strip() else []
        if not seps:
            tokens = text.split(); chunks = []; start = 0
            while start < len(tokens):
                end = min(start + self.chunk_size, len(tokens))
                chunks.append(" ".join(tokens[start:end]))
                if end == len(tokens): break
                start += self.chunk_size - self.overlap
            return chunks
        sep, rest = seps[0], seps[1:]
        parts  = list(text) if sep == "" else text.split(sep)
        merged = self._merge(parts, sep)
        result = []
        for p in merged:
            result.extend(self._split(p, rest) if self._wc(p) > self.chunk_size else ([p] if p.strip() else []))
        return result

    def _merge(self, parts, sep):
        merged = []; cur = ""
        for p in parts:
            cand = (cur + sep + p).strip() if cur else p.strip()
            if self._wc(cand) <= self.chunk_size:
                cur = cand
            else:
                if cur: merged.append(cur)
                cur = p.strip()
        if cur: merged.append(cur)
        return merged
