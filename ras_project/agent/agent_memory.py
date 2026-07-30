"""agent/agent_memory.py — Accumulates evidence across tool calls in one ReAct loop."""
from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class AgentMemory:
    question:        str
    observations:    List[Dict[str, Any]] = field(default_factory=list)
    tool_call_log:   List[Dict[str, Any]] = field(default_factory=list)
    retrieved_chunks: List[Dict[str, Any]] = field(default_factory=list)
    web_results:     List[Dict[str, Any]] = field(default_factory=list)
    iteration:       int = 0
    max_iterations:  int = 8

    def add_observation(self, tool: str, query: str, result: str, chunks: List = None):
        self.observations.append({
            "tool":   tool,
            "query":  query,
            "result": result[:2000],   # cap per observation
        })
        self.tool_call_log.append({"tool": tool, "query": query})
        if chunks:
            # Deduplicate by chunk_id
            existing = {c.get("chunk_id") for c in self.retrieved_chunks}
            for c in chunks:
                cid = c.get("chunk_id", c["text"][:30])
                if cid not in existing:
                    self.retrieved_chunks.append(c)
                    existing.add(cid)
        self.iteration += 1

    def context_window(self) -> str:
        """Build a compact summary of everything gathered so far."""
        parts = [f"Question: {self.question}\n"]
        parts.append("=== Gathered Evidence ===")
        for i, obs in enumerate(self.observations, 1):
            parts.append(f"\n[{i}] Tool: {obs['tool']} | Query: {obs['query']}\n{obs['result']}")
        return "\n".join(parts)

    def best_chunks(self, top_k: int = 10) -> List[Dict[str, Any]]:
        """Return top chunks sorted by hybrid/cosine score."""
        scored = sorted(
            self.retrieved_chunks,
            key=lambda c: c.get("hybrid_score", c.get("cosine_score", 0.0)),
            reverse=True,
        )
        return scored[:top_k]

    def tools_used(self) -> List[str]:
        return [t["tool"] for t in self.tool_call_log]

    def should_stop(self) -> bool:
        return self.iteration >= self.max_iterations