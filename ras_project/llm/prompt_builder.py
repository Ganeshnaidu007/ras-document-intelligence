"""llm/prompt_builder.py — Builds LLM prompts from retrieved context chunks."""
from typing import List, Dict, Any
from config.prompts import ANSWER_GENERATION_SYSTEM, ANSWER_GENERATION_SYSTEM_CONCISE


class PromptBuilder:
    def __init__(self, max_context_tokens: int = 6000, response_style: str = "concise"):
        self.max_context_tokens = max_context_tokens
        self.response_style     = response_style  # "concise" (default) or "detailed"

    def build(self, question: str, chunks: List[Dict[str, Any]]) -> Dict[str, str]:
        context = self._context(chunks)
        sep = "=" * 70
        user = (
            f"Retrieved Document Chunks:\n{sep}\n{context}\n{sep}\n\n"
            f"Question: {question}\n\n"
            f"Instructions: Synthesize the above chunks to answer the question. "
            f"Cite page/section numbers where visible. Be precise and factual."
        )
        system = (ANSWER_GENERATION_SYSTEM if self.response_style == "detailed"
                  else ANSWER_GENERATION_SYSTEM_CONCISE)
        return {"system": system, "user": user}

    def _context(self, chunks: List[Dict[str, Any]]) -> str:
        parts, total = [], 0
        for i, c in enumerate(chunks, 1):
            text = c.get("text", "").strip()
            est  = len(text.split())
            if total + est > self.max_context_tokens:
                break
            source  = c.get("source", "unknown")
            page    = c.get("page_number", "?")
            section = c.get("parent_section", "")
            meta    = f"Chunk {i} | {source}, Page {page}"
            if section:
                meta += f", Section: {section}"
            parts.append(f"[{meta}]\n{text}")
            total += est
        return "\n\n---\n\n".join(parts)