"""agent/conversation_memory.py — Cross-question conversation memory for the agent.

Stores all prior Q&A turns in the session so the agent can say:
"Based on your previous question about X, this also relates because..."
"""
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class Turn:
    question:   str
    answer:     str
    chunks:     List[Dict[str, Any]]
    trace:      List[Dict[str, Any]]
    turn_num:   int


class ConversationMemory:
    """Session-level memory — persists across all questions in one run."""

    def __init__(self, max_turns_in_context: int = 5):
        self.turns: List[Turn] = []
        self.max_turns_in_context = max_turns_in_context

    def add_turn(self, question: str, answer: str,
                 chunks: List[Dict] = None, trace: List[Dict] = None):
        self.turns.append(Turn(
            question=question,
            answer=answer,
            chunks=chunks or [],
            trace=trace or [],
            turn_num=len(self.turns) + 1,
        ))

    def context_for_agent(self) -> str:
        """Return a compact summary of prior turns for injection into agent prompt."""
        if not self.turns:
            return ""
        recent = self.turns[-self.max_turns_in_context:]
        lines = ["=== Conversation History (prior questions in this session) ==="]
        for t in recent:
            lines.append(f"\n[Turn {t.turn_num}]")
            lines.append(f"Q: {t.question}")
            # Truncate answers to 300 chars to save context window
            lines.append(f"A: {t.answer[:300]}{'...' if len(t.answer)>300 else ''}")
        lines.append("=== End of History ===\n")
        return "\n".join(lines)

    def all_retrieved_chunks(self) -> List[Dict[str, Any]]:
        """Unique chunks across all turns — for building richer context."""
        seen, chunks = set(), []
        for t in self.turns:
            for c in t.chunks:
                cid = c.get("chunk_id", c.get("text","")[:30])
                if cid not in seen:
                    seen.add(cid)
                    chunks.append(c)
        return chunks

    def summary(self) -> str:
        """One-line summary of the conversation so far."""
        if not self.turns:
            return "No prior conversation."
        topics = [t.question[:50] for t in self.turns[-3:]]
        return f"{len(self.turns)} prior question(s). Recent: {'; '.join(topics)}"

    def clear(self):
        self.turns.clear()

    def __len__(self):
        return len(self.turns)