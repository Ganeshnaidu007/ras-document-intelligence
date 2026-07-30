"""chunking/sliding_window.py — Sliding window chunker."""
from typing import List

class SlidingWindowChunker:
    def __init__(self, window_size: int = 500, step: int = 250):
        self.window_size = max(1, window_size)
        self.step        = max(1, step)

    def chunk(self, text: str) -> List[str]:
        tokens = text.split()
        if not tokens: return []
        chunks = []; start = 0
        while start < len(tokens):
            end = min(start + self.window_size, len(tokens))
            chunks.append(" ".join(tokens[start:end]))
            if end == len(tokens): break
            start += self.step
        return chunks
