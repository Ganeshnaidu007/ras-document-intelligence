"""llm/answer_generator.py — Multi-provider LLM with streaming."""
import concurrent.futures
from typing import List, Dict, Any, Generator
from llm.prompt_builder import PromptBuilder
from config.settings import (LLM_MAX_TOKENS, LLM_TEMPERATURE,
                               OPENAI_API_KEY, GOOGLE_API_KEY,
                               GROQ_API_KEY, OPENROUTER_API_KEY,
                               GEMINI_MODELS, GROQ_MODELS, OPENROUTER_MODELS)
from utils.logger import get_logger
logger = get_logger(__name__)


# ── Non-streaming ─────────────────────────────────────────────────────────────

def _call_gemini(system: str, user: str) -> str:
    from google import genai
    client = genai.Client(api_key=GOOGLE_API_KEY)
    last_err = None
    for m in GEMINI_MODELS:
        try:
            return client.models.generate_content(
                model=m, contents=f"{system}\n\n{user}").text.strip()
        except Exception as e:
            last_err = e
    raise RuntimeError(f"All Gemini models failed: {last_err}")


def _call_groq(system: str, user: str) -> str:
    if not GROQ_API_KEY: raise ValueError("GROQ_API_KEY not set")
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    last_err = None
    for m in GROQ_MODELS:
        try:
            resp = client.chat.completions.create(
                model=m, max_tokens=LLM_MAX_TOKENS, temperature=LLM_TEMPERATURE,
                messages=[{"role":"system","content":system},{"role":"user","content":user}])
            return resp.choices[0].message.content.strip()
        except Exception as e:
            last_err = e
    raise RuntimeError(f"All Groq models failed: {last_err}")


def _call_openrouter(system: str, user: str) -> str:
    if not OPENROUTER_API_KEY: raise ValueError("OPENROUTER_API_KEY not set")
    import openai
    client = openai.OpenAI(api_key=OPENROUTER_API_KEY,
                           base_url="https://openrouter.ai/api/v1")
    last_err = None
    for m in OPENROUTER_MODELS:
        try:
            resp = client.chat.completions.create(
                model=m, max_tokens=LLM_MAX_TOKENS, temperature=LLM_TEMPERATURE,
                messages=[{"role":"system","content":system},{"role":"user","content":user}],
                extra_headers={"HTTP-Referer":"https://ras-doc-intel.app","X-Title":"RAS"})
            return resp.choices[0].message.content.strip()
        except Exception as e:
            last_err = e
    raise RuntimeError(f"All OpenRouter models failed: {last_err}")


def _call_openai(system: str, user: str) -> str:
    if not OPENAI_API_KEY: raise ValueError("OPENAI_API_KEY not set")
    import openai
    resp = openai.OpenAI(api_key=OPENAI_API_KEY).chat.completions.create(
        model="gpt-4o-mini", temperature=LLM_TEMPERATURE, max_tokens=LLM_MAX_TOKENS,
        messages=[{"role":"system","content":system},{"role":"user","content":user}])
    return resp.choices[0].message.content.strip()


# ── Streaming ─────────────────────────────────────────────────────────────────

def stream_groq(system: str, user: str) -> Generator[str, None, None]:
    if not GROQ_API_KEY:
        yield "[GROQ_API_KEY not set in secrets.toml]"; return
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        for m in GROQ_MODELS:
            try:
                stream = client.chat.completions.create(
                    model=m, max_tokens=LLM_MAX_TOKENS, temperature=LLM_TEMPERATURE,
                    messages=[{"role":"system","content":system},{"role":"user","content":user}],
                    stream=True)
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta: yield delta
                return
            except Exception as e:
                logger.warning(f"Groq stream {m}: {e}")
    except ImportError:
        pass
    yield from _fallback_stream(system, user)


def stream_openrouter(system: str, user: str) -> Generator[str, None, None]:
    if not OPENROUTER_API_KEY:
        yield "[OPENROUTER_API_KEY not set in secrets.toml]"; return
    try:
        import openai
        client = openai.OpenAI(api_key=OPENROUTER_API_KEY,
                               base_url="https://openrouter.ai/api/v1")
        stream = client.chat.completions.create(
            model=OPENROUTER_MODELS[0], max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            extra_headers={"HTTP-Referer":"https://ras-doc-intel.app","X-Title":"RAS"},
            stream=True)
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta: yield delta
    except Exception as e:
        logger.warning(f"OpenRouter stream: {e}")
        yield from _fallback_stream(system, user)


def stream_openai(system: str, user: str) -> Generator[str, None, None]:
    if not OPENAI_API_KEY:
        yield "[OPENAI_API_KEY not set in secrets.toml]"; return
    import openai
    stream = openai.OpenAI(api_key=OPENAI_API_KEY).chat.completions.create(
        model="gpt-4o-mini", temperature=LLM_TEMPERATURE, max_tokens=LLM_MAX_TOKENS,
        messages=[{"role":"system","content":system},{"role":"user","content":user}],
        stream=True)
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta: yield delta


def _fallback_stream(system: str, user: str) -> Generator[str, None, None]:
    """Word-by-word fake streaming for providers without native stream support."""
    try:
        text = _call_gemini(system, user)
    except Exception:
        try:
            text = _call_groq(system, user)
        except Exception as e:
            text = f"[Error: {e}]"
    for word in text.split(" "):
        yield word + " "


def get_stream(provider: str, system: str, user: str) -> Generator[str, None, None]:
    if provider == "groq":       return stream_groq(system, user)
    if provider == "openrouter": return stream_openrouter(system, user)
    if provider == "openai":     return stream_openai(system, user)
    return _fallback_stream(system, user)  # gemini


# ── Fallback chain ────────────────────────────────────────────────────────────

PROVIDER_CHAIN = [
    ("groq",       _call_groq,       lambda: GROQ_API_KEY),
    ("gemini",     _call_gemini,     lambda: GOOGLE_API_KEY),
    ("openrouter", _call_openrouter, lambda: OPENROUTER_API_KEY),
    ("openai",     _call_openai,     lambda: OPENAI_API_KEY),
]


class AnswerGenerator:
    def __init__(self, provider: str = "groq", response_style: str = "concise"):
        self.provider       = provider.lower()
        self.prompt_builder = PromptBuilder(response_style=response_style)

    def generate(self, question: str, chunks: List[Dict[str, Any]]) -> str:
        if not chunks:
            return "No relevant information found in the provided documents."
        prompt = self.prompt_builder.build(question, chunks)
        s, u = prompt["system"], prompt["user"]
        try:
            if self.provider == "groq":       return _call_groq(s, u)
            if self.provider == "gemini":     return _call_gemini(s, u)
            if self.provider == "openrouter": return _call_openrouter(s, u)
            if self.provider == "openai":     return _call_openai(s, u)
        except Exception as e:
            logger.warning(f"{self.provider} failed: {e} — trying fallbacks")
        for name, fn, has_key in PROVIDER_CHAIN:
            if name == self.provider or not has_key(): continue
            try:
                return fn(s, u)
            except Exception as e2:
                logger.warning(f"{name} fallback: {e2}")
        return "[Error: all LLM providers failed. Check secrets.toml]"

    def generate_streaming(self, question: str, chunks: List[Dict[str, Any]]) -> Generator[str, None, None]:
        if not chunks:
            yield "No relevant information found."; return
        prompt = self.prompt_builder.build(question, chunks)
        yield from get_stream(self.provider, prompt["system"], prompt["user"])

    def generate_batch(self, questions_chunks: List[tuple]) -> List[str]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            futures = [ex.submit(self.generate, q, c) for q, c in questions_chunks]
            return [f.result() for f in futures]