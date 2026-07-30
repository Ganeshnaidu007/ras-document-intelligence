"""retrieval/multi_query.py — Multi-query expansion, fastest available provider."""
import json
from typing import List
from utils.logger import get_logger
from config.prompts  import MULTI_QUERY_SYSTEM, MULTI_QUERY_USER
from config.settings import (GROQ_API_KEY, GOOGLE_API_KEY, OPENROUTER_API_KEY,
                               OPENAI_API_KEY, GROQ_MODELS, GEMINI_MODELS)
logger = get_logger(__name__)


def _parse_json_list(text: str) -> List[str]:
    text = text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(text)


class MultiQueryExpander:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def expand(self, question: str) -> List[str]:
        if not self.enabled:
            return [question]
        try:
            expanded = self._call(question)
            if question not in expanded:
                expanded.insert(0, question)
            return expanded[:5]
        except Exception as e:
            logger.warning(f"Multi-query expand failed: {e}")
            return [question]

    def _call(self, question: str) -> List[str]:
        prompt = MULTI_QUERY_USER.format(question=question)
        # Groq is fastest for this lightweight task
        if GROQ_API_KEY:
            try:
                from groq import Groq
                client = Groq(api_key=GROQ_API_KEY)
                for m in GROQ_MODELS:
                    try:
                        resp = client.chat.completions.create(
                            model=m, max_tokens=200, temperature=0,
                            messages=[{"role": "system", "content": MULTI_QUERY_SYSTEM},
                                      {"role": "user",   "content": prompt}],
                        )
                        return _parse_json_list(resp.choices[0].message.content)
                    except Exception as e:
                        logger.warning(f"Groq multi-query {m}: {e}")
            except ImportError:
                pass

        if GOOGLE_API_KEY:
            from google import genai
            client = genai.Client(api_key=GOOGLE_API_KEY)
            for m in GEMINI_MODELS:
                try:
                    resp = client.models.generate_content(
                        model=m, contents=f"{MULTI_QUERY_SYSTEM}\n\n{prompt}")
                    return _parse_json_list(resp.text)
                except Exception as e:
                    logger.warning(f"Gemini multi-query {m}: {e}")

        if OPENROUTER_API_KEY:
            import openai
            client = openai.OpenAI(api_key=OPENROUTER_API_KEY,
                                   base_url="https://openrouter.ai/api/v1")
            try:
                resp = client.chat.completions.create(
                    model="meta-llama/llama-3.1-8b-instruct",
                    max_tokens=200, temperature=0,
                    messages=[{"role": "system", "content": MULTI_QUERY_SYSTEM},
                              {"role": "user",   "content": prompt}],
                )
                return _parse_json_list(resp.choices[0].message.content)
            except Exception as e:
                logger.warning(f"OpenRouter multi-query: {e}")

        if OPENAI_API_KEY:
            import openai
            resp = openai.OpenAI(api_key=OPENAI_API_KEY).chat.completions.create(
                model="gpt-4o-mini", max_tokens=200, temperature=0,
                messages=[{"role": "system", "content": MULTI_QUERY_SYSTEM},
                          {"role": "user",   "content": prompt}],
            )
            return _parse_json_list(resp.choices[0].message.content)

        raise ValueError("No API key available for multi-query expansion")