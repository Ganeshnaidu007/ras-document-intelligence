"""agent/react_agent.py — ReAct Agentic RAG with cross-question conversation memory."""
import json
from typing import Dict, Any, List, Generator, Optional
from utils.logger import get_logger
from agent.agent_memory       import AgentMemory
from agent.conversation_memory import ConversationMemory
from agent.tools              import tool_schema_for_llm
from config.settings import (
    GROQ_API_KEY, GOOGLE_API_KEY, OPENROUTER_API_KEY, OPENAI_API_KEY,
    GROQ_MODELS, GEMINI_MODELS,
)
logger = get_logger(__name__)

AGENT_SYSTEM = """You are an expert research agent with access to document retrieval, \
web search, and reading tools. Your goal is to produce the most accurate, well-supported \
answer possible, grounded entirely in what the tools actually return.

## Available Tools
{tool_schema}

## Conversation History
{conversation_history}

## Response Format (JSON ONLY)
{{
  "thought": "Your reasoning about what you know so far and what you need next.",
  "tool":    "tool_name",
  "input":   "exact input to pass to the tool"
}}

## Rules
- Always check conversation history — if the user refers to a prior topic, use that context.
- Use retrieve_documents first. Use web_search when documents lack the answer.
- Use read_url to get full content from a URL found in search results.
- Use refine_query if retrieval was weak, then retry retrieve_documents.
- Use final_answer as soon as you have enough evidence to answer confidently —
  don't force extra tool calls on questions a single retrieval already answers.
- Never repeat the same tool+input combination twice.
- Iteration {iteration}/{max_iterations} — plan accordingly.
"""

SYNTHESIS_SYSTEM = """You are a senior research analyst producing comprehensive answers.

## Output Structure
### Summary
2-3 sentences directly answering the question.

### Detailed Explanation
4-8 thorough paragraphs with all relevant facts, mechanisms, numbers, and context.
Cross-reference with prior conversation turns where relevant.

### Key Findings
6-10 specific, concrete bullet points drawn directly from the evidence.

### Supporting Evidence
Quote or closely paraphrase the most relevant passages.

### Limitations
What the sources do NOT cover or where evidence is weak.

## Rules
- Do not cite sources inline (no "(Source: ...)" markers, footnotes, or bracketed
  references anywhere in the answer) — the underlying passages are shown to the
  user separately, alongside the answer.
- Write AT LEAST 500 words on technical questions.
- Never say "the context says" — synthesise and explain directly, in your own words.
- Include actual numbers, model names, and dates from the sources.
- If prior conversation is provided, reference it naturally where relevant.
- If something is inferred rather than stated outright, flag it: "This suggests…"
- Never fabricate facts not present in the retrieved evidence.
"""

# Chat mode wants a fast, direct answer, not a forced 500+ word report — that
# length requirement was the main source of chat latency, since every reply
# had to hit a minimum word count regardless of how simple the question was.
SYNTHESIS_SYSTEM_CONCISE = """You are a helpful, precise research assistant answering a
conversational question using retrieved document/web evidence.

## Rules
- Answer directly in 1-4 short paragraphs — only as long as the question
  actually requires. A one-line factual question deserves a one-line answer.
- Do NOT use section headers like "Summary" or "Key Findings" — just answer
  the question in plain, natural prose, the way you'd explain it to a
  colleague who already has the documents open.
- Do not cite sources inline (no "(Source: ...)" markers, footnotes, page
  numbers, or bracketed references anywhere in the answer) — the underlying
  passages are shown to the user separately, alongside the answer.
- Never say "the context says" or "the documents state" — synthesise and
  explain directly, in your own words, as if you simply know the answer.
- Include actual numbers, names, and dates from the sources when relevant.
- If prior conversation is provided, reference it naturally where relevant —
  don't repeat information you already gave earlier in this chat.
- Never fabricate facts. If the evidence is thin or missing, say so briefly
  instead of padding the answer or guessing.
"""


import time as _time
import threading as _threading

# ── Per-process model cooldown tracker ───────────────────────────────────────
# Maps model_id → earliest time it can be retried (epoch seconds).
# Shared across all AgenticRAG instances so parallel questions don't all
# pile on a model that just returned 429.
_model_cooldown: Dict[str, float] = {}
_cooldown_lock = _threading.Lock()
# Models that returned 400 "decommissioned" — skip permanently this process.
_dead_models: set = set()


def _is_available(model: str) -> bool:
    """Return True if model is not dead and not in cooldown."""
    if model in _dead_models:
        return False
    with _cooldown_lock:
        ready_at = _model_cooldown.get(model, 0)
    return _time.time() >= ready_at


def _set_cooldown(model: str, seconds: float) -> None:
    with _cooldown_lock:
        _model_cooldown[model] = _time.time() + seconds


def _parse_retry_delay(err_str: str, default: float = 10.0) -> float:
    """Extract retry-after seconds from a 429 error message."""
    import re
    m = re.search(r"retry[^\d]*(\d+(?:\.\d+)?)\s*s", str(err_str), re.I)
    return float(m.group(1)) if m else default


def _llm_call(messages: List[Dict], provider: str, max_tokens: int = 400) -> str:
    """
    Smart LLM dispatcher with:
    - Per-model cooldown after 429 (respects retry-after delay from error message)
    - Permanent skip for 400 decommissioned models
    - Automatic cross-provider fallback when primary is rate-limited
    """
    system = messages[0]["content"]
    user   = messages[-1]["content"]

    # ── Try Groq ──────────────────────────────────────────────────────────────
    if provider == "groq" and GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            for m in GROQ_MODELS:
                if not _is_available(m):
                    logger.info(f"Skipping {m} (cooldown/dead)")
                    continue
                try:
                    resp = client.chat.completions.create(
                        model=m, max_tokens=max_tokens, temperature=0.1,
                        messages=messages)
                    return resp.choices[0].message.content.strip()
                except Exception as e:
                    err = str(e)
                    if "decommissioned" in err or "400" in err:
                        _dead_models.add(m)
                        logger.warning(f"Groq {m}: DECOMMISSIONED — skipping permanently")
                    elif "429" in err or "rate_limit" in err.lower():
                        delay = _parse_retry_delay(err, default=15.0)
                        _set_cooldown(m, delay)
                        logger.warning(f"Groq {m}: 429 — cooldown {delay:.0f}s")
                    else:
                        logger.warning(f"Groq agent {m}: {e}")
        except ImportError:
            pass

    # ── Try Gemini ────────────────────────────────────────────────────────────
    if GOOGLE_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GOOGLE_API_KEY)
            for m in GEMINI_MODELS:
                if not _is_available(m):
                    logger.info(f"Skipping {m} (cooldown/dead)")
                    continue
                try:
                    return client.models.generate_content(
                        model=m, contents=f"{system}\n\n{user}").text.strip()
                except Exception as e:
                    err = str(e)
                    if "429" in err or "RESOURCE_EXHAUSTED" in err:
                        delay = _parse_retry_delay(err, default=45.0)
                        _set_cooldown(m, delay)
                        logger.warning(f"Gemini {m}: 429 — cooldown {delay:.0f}s")
                    elif "503" in err or "UNAVAILABLE" in err:
                        _set_cooldown(m, 20.0)
                        logger.warning(f"Gemini {m}: 503 — cooldown 20s")
                    else:
                        logger.warning(f"Gemini agent {m}: {e}")
        except Exception:
            pass

    # ── Try OpenRouter ────────────────────────────────────────────────────────
    if OPENROUTER_API_KEY:
        try:
            import openai
            client = openai.OpenAI(api_key=OPENROUTER_API_KEY,
                                   base_url="https://openrouter.ai/api/v1")
            resp = client.chat.completions.create(
                model="meta-llama/llama-3.3-70b-instruct",
                messages=messages, max_tokens=max_tokens, temperature=0.1)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"OpenRouter agent: {e}")

    # ── Try OpenAI ────────────────────────────────────────────────────────────
    if OPENAI_API_KEY:
        import openai
        resp = openai.OpenAI(api_key=OPENAI_API_KEY).chat.completions.create(
            model="gpt-4o-mini", messages=messages,
            max_tokens=max_tokens, temperature=0.1)
        return resp.choices[0].message.content.strip()

    raise RuntimeError("No LLM available — all models are rate-limited or unavailable")


def _parse_action(text: str) -> Dict[str, str]:
    text = text.strip()
    if "```" in text:
        text = text.split("```")[1].replace("json","").strip()
    try:
        return json.loads(text)
    except Exception:
        import re
        tool    = re.search(r'"tool"\s*:\s*"([^"]+)"', text)
        inp     = re.search(r'"input"\s*:\s*"([^"]+)"', text)
        thought = re.search(r'"thought"\s*:\s*"([^"]+)"', text)
        return {
            "thought": thought.group(1) if thought else "",
            "tool":    tool.group(1)    if tool    else "final_answer",
            "input":   inp.group(1)     if inp     else "",
        }


class AgenticRAG:
    def __init__(self, retriever, reranker, web_searcher, embedder,
                 provider: str = "groq", max_iterations: int = 8,
                 stream: bool = False,
                 conversation_memory: Optional[ConversationMemory] = None,
                 response_style: str = "detailed",
                 fast_first_step: bool = False):
        self.retriever           = retriever
        self.reranker            = reranker
        self.web_searcher        = web_searcher
        self.embedder            = embedder
        self.provider            = provider
        self.max_iterations      = max_iterations
        self.stream              = stream
        self.conversation_memory = conversation_memory or ConversationMemory()
        self.response_style      = response_style  # "detailed" (batch) or "concise" (chat)
        # Skips the LLM call that just decides "retrieve first" — for a
        # brand-new question that's always the right first move anyway, so
        # asking the model to confirm it wastes a full round-trip. This is
        # the main lever for chat-mode latency: it turns the common case
        # (one retrieval is enough to answer) from 3 LLM calls (reason →
        # reason → synthesise) into 1 (synthesise only). If that single
        # retrieval comes back empty, it falls through to the normal
        # reasoning loop so the agent can still decide to web-search,
        # refine the query, etc.
        self.fast_first_step     = fast_first_step

    def _fast_retrieve_step(self, question: str, memory: AgentMemory) -> Optional[Dict[str, str]]:
        """Runs retrieve_documents directly, no LLM call. Returns the trace
        step describing it, or None if fast_first_step is off."""
        if not self.fast_first_step or memory.iteration != 0:
            return None
        step = {"iteration": 1, "thought": "Checking the documents first.",
                "tool": "retrieve_documents", "input": question}
        obs, chunks = self._execute_tool("retrieve_documents", question, memory)
        memory.add_observation("retrieve_documents", question, obs, chunks)
        return step

    def run(self, question: str, status_callback=None) -> Dict[str, Any]:
        memory = AgentMemory(question=question, max_iterations=self.max_iterations)
        trace  = []

        def _s(msg):
            logger.info(msg)
            if status_callback: status_callback(msg)

        _s(f"🤖 Agent: {question[:80]}…")

        fast_step = self._fast_retrieve_step(question, memory)
        if fast_step:
            trace.append(fast_step)
            _s("  [1] 🔎 Checking the documents…")

        while not memory.should_stop() and not (fast_step and memory.retrieved_chunks):
            action  = self._reason(memory)
            thought = action.get("thought", "")
            tool    = action.get("tool",    "final_answer")
            inp     = action.get("input",   question)

            trace.append({"iteration": memory.iteration+1,
                          "thought": thought, "tool": tool, "input": inp})
            _s(f"  [{memory.iteration+1}] 🧠 {thought[:100]}… → **{tool}**")

            if tool == "final_answer":
                break

            obs, chunks = self._execute_tool(tool, inp, memory)
            memory.add_observation(tool, inp, obs, chunks)

        _s("✍️ Writing the answer…" if self.response_style == "concise" else "✍️ Synthesising detailed answer…")
        answer = self._synthesise(question, memory)

        # Store in conversation memory for future questions
        self.conversation_memory.add_turn(
            question=question, answer=answer,
            chunks=memory.best_chunks(10), trace=trace)

        return {"answer": answer, "trace": trace,
                "chunks": memory.best_chunks(10), "iterations": memory.iteration}

    def run_streaming(self, question: str, status_callback=None) -> Generator[str, None, None]:
        memory = AgentMemory(question=question, max_iterations=self.max_iterations)
        trace  = []

        def _s(msg):
            if status_callback: status_callback(msg)

        fast_step = self._fast_retrieve_step(question, memory)
        if fast_step:
            trace.append(fast_step)
            yield ("trace", fast_step)

        while not memory.should_stop() and not (fast_step and memory.retrieved_chunks):
            action  = self._reason(memory)
            thought = action.get("thought", "")
            tool    = action.get("tool",    "final_answer")
            inp     = action.get("input",   question)

            step = {"iteration": memory.iteration+1,
                    "thought": thought, "tool": tool, "input": inp}
            trace.append(step)
            yield ("trace", step)
            _s(f"[{memory.iteration+1}] {tool}: {inp[:60]}…")

            if tool == "final_answer":
                break

            obs, chunks = self._execute_tool(tool, inp, memory)
            memory.add_observation(tool, inp, obs, chunks)

        yield ("trace", {"thought": "Synthesising final comprehensive answer…",
                          "tool": "final_answer", "input": question,
                          "iteration": memory.iteration+1})
        full = ""
        for token in self._synthesise_streaming(question, memory):
            full += token
            yield ("token", token)

        self.conversation_memory.add_turn(
            question=question, answer=full,
            chunks=memory.best_chunks(10), trace=trace)

        yield ("done", {"answer": full, "trace": trace,
                         "chunks": memory.best_chunks(10),
                         "iterations": memory.iteration})

    def _reason(self, memory: AgentMemory) -> Dict[str, str]:
        conv_ctx = self.conversation_memory.context_for_agent()
        system = AGENT_SYSTEM.format(
            tool_schema=tool_schema_for_llm(),
            conversation_history=conv_ctx or "No prior conversation.",
            iteration=memory.iteration+1,
            max_iterations=self.max_iterations,
        )
        used = memory.tools_used()
        has_docs = "retrieve_documents" in used
        has_web  = "web_search" in used
        guidance = (
            f"\nTools used so far: {used or 'none'}"
            f"\nChunks gathered: {len(memory.retrieved_chunks)}"
            + ("\nHINT: You have doc chunks — consider web_search for more context." if has_docs and not has_web and memory.iteration == 1 else "")
            + ("\nHINT: Enough context gathered — consider final_answer." if memory.iteration >= max(1, self.max_iterations - 1) else "")
        )
        user = memory.context_window() + guidance + "\n\nWhat is your next action? JSON only."
        messages = [{"role":"system","content":system},{"role":"user","content":user}]
        try:
            raw = _llm_call(messages, self.provider, max_tokens=300)
            return _parse_action(raw)
        except Exception as e:
            logger.error(f"Agent reasoning failed: {e}")
            return {"thought":"Error — going to final answer","tool":"final_answer","input":memory.question}

    def _execute_tool(self, tool: str, inp: str, memory: AgentMemory):
        try:
            if tool == "retrieve_documents": return self._tool_retrieve(inp)
            if tool == "web_search":         return self._tool_web_search(inp)
            if tool == "read_url":           return self._tool_read_url(inp)
            if tool == "refine_query":       return self._tool_refine(inp, memory)
            if tool == "summarise_context":  return self._tool_summarise(inp)
            return f"Unknown tool: {tool}", []
        except Exception as e:
            logger.error(f"Tool {tool} error: {e}")
            return f"Tool error: {e}", []

    def _tool_retrieve(self, query: str):
        # top_k=14 (was 20) — the cross-encoder rerank step is the expensive
        # part of this call; 14 candidates still comfortably covers the
        # final top-8 while cutting reranker compute by ~30%.
        chunks = self.retriever.retrieve(query, top_k=14)
        ranked = self.reranker.rerank(query, chunks, top_k=8)
        obs = "\n\n".join(
            f"[Chunk {i+1} | {c.get('source','?')}, p.{c.get('page_number','?')}]\n{c.get('text','')[:500]}"
            for i, c in enumerate(ranked))
        return obs or "No relevant chunks found.", ranked

    def _tool_web_search(self, query: str):
        if not self.web_searcher:
            return "Web search not enabled.", []
        results = self.web_searcher.search(query, num_results=5)
        obs = "\n\n".join(
            f"[{i+1}] {r['title']}\n{r['snippet']}\nURL: {r['link']}"
            for i, r in enumerate(results))
        chunks = self.web_searcher.to_chunks(query, num_results=5)
        return obs or "No web results.", chunks

    def _tool_read_url(self, url: str):
        try:
            from embeddings.jina_embeddings import JinaReader
            result = JinaReader().read_url(url)
            text   = result.get("text","")[:3000]
            if not text: return "Could not read URL.", []
            chunk = {"chunk_id":url[-20:],"text":text,"source":url,
                     "page_number":"web","parent_section":result.get("title",""),
                     "author":"Jina Reader","token_count":len(text.split()),"embedding":None}
            return text, [chunk]
        except Exception as e:
            return f"Jina Reader error: {e}", []

    def _tool_refine(self, query: str, memory: AgentMemory):
        system = "Rewrite this query into 3 better search queries. Return JSON array only."
        messages = [{"role":"system","content":system},{"role":"user","content":query}]
        try:
            raw = _llm_call(messages, self.provider, max_tokens=150)
            queries = json.loads(raw.strip().replace("```json","").replace("```","").strip())
        except Exception:
            queries = [query]
        all_chunks, obs_parts = [], []
        for q in queries[:3]:
            chunks = self.retriever.retrieve(q, top_k=10)
            all_chunks.extend(chunks)
            obs_parts.append(f"Query '{q}': {len(chunks)} chunks")
        ranked = self.reranker.rerank(query, all_chunks, top_k=8)
        obs = "\n".join(obs_parts) + "\n\n" + "\n\n".join(
            f"[{i+1}] {c.get('text','')[:400]}" for i, c in enumerate(ranked))
        return obs, ranked

    def _tool_summarise(self, text: str):
        system = "Summarise this text concisely, preserving all key facts."
        messages = [{"role":"system","content":system},{"role":"user","content":text[:6000]}]
        try:
            return _llm_call(messages, self.provider, max_tokens=500), []
        except Exception:
            return text[:2000], []

    def _build_synthesis_prompt(self, question: str, memory: AgentMemory):
        chunks  = memory.best_chunks(10)
        context = "\n\n---\n\n".join(
            f"[Source {i+1}: {c.get('source','?')}, Page {c.get('page_number','?')}]\n{c.get('text','')}"
            for i, c in enumerate(chunks))
        web_obs = [o for o in memory.observations if o["tool"] in ("web_search","read_url")]
        web_ctx = ("\n\n=== Web Evidence ===\n" + "\n\n".join(
            f"[Web {i+1}]: {o['result'][:800]}" for i, o in enumerate(web_obs))
            if web_obs else "")
        conv_ctx = self.conversation_memory.context_for_agent()
        concise = self.response_style == "concise"
        user = (
            f"{conv_ctx}"
            f"Current Question: {question}\n\n"
            f"=== Document Evidence ===\n{context}{web_ctx}\n\n"
            f"Agent gathered {len(chunks)} document chunks and {len(web_obs)} web sources "
            f"over {memory.iteration} reasoning steps.\n\n"
            + ("Answer directly and concisely, following your instructions."
               if concise else
               "Write a comprehensive, detailed answer following your instructions.")
        )
        return (SYNTHESIS_SYSTEM_CONCISE if concise else SYNTHESIS_SYSTEM), user

    def _synthesise(self, question: str, memory: AgentMemory) -> str:
        system, user = self._build_synthesis_prompt(question, memory)
        messages = [{"role":"system","content":system},{"role":"user","content":user}]
        synth_provider = "gemini" if GOOGLE_API_KEY else self.provider
        max_tok = 700 if self.response_style == "concise" else 2000
        try:
            return _llm_call(messages, synth_provider, max_tokens=max_tok)
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return _llm_call(messages, self.provider, max_tokens=max_tok)

    def _synthesise_streaming(self, question: str, memory: AgentMemory) -> Generator[str, None, None]:
        from llm.answer_generator import get_stream, _fallback_stream
        system, user = self._build_synthesis_prompt(question, memory)
        if self.provider == "gemini":
            yield from _fallback_stream(system, user)
        else:
            yield from get_stream(self.provider, system, user)