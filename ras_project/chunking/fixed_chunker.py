"""chunking/fixed_chunker.py — Fixed-size word-token chunker with overlap."""
from typing import List

class FixedChunker:
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap    = max(0, min(overlap, chunk_size - 1))

    def chunk(self, text: str) -> List[str]:
        tokens = text.split()
        if not tokens:
            return []
        chunks, start = [], 0
        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunks.append(" ".join(tokens[start:end]))
            if end == len(tokens):
                break
            start += self.chunk_size - self.overlap
        return chunks
