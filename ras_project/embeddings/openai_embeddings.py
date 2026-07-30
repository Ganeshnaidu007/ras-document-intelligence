"""embeddings/openai_embeddings.py — Cloud embedders: OpenAI, Gemini, Cohere.

NOTE: this file previously contained a stray copy of config/prompts.py's
contents instead of any embedding code — OpenAIEmbedder, GeminiEmbedder,
and CohereEmbedder (all imported by embeddings/embedding_factory.py)
simply didn't exist. Selecting "OpenAI text-embedding-3-small", "Gemini
text-embedding-004", or "Cohere Embed" as the embedding model would have
raised ImportError the moment a document was processed. Rebuilt to match
the same embed_batch()/embed_single() interface every other embedder in
this package uses (see embeddings/local_embeddings.py, jina_embeddings.py).
"""
from typing import List
from utils.logger import get_logger
from config.settings import OPENAI_API_KEY, GOOGLE_API_KEY, COHERE_API_KEY

logger = get_logger(__name__)

OPENAI_EMBED_MODEL = "text-embedding-3-small"   # 1536 dims
OPENAI_EMBED_DIMS  = 1536

GEMINI_EMBED_MODEL = "text-embedding-004"       # 768 dims
GEMINI_EMBED_DIMS  = 768

COHERE_EMBED_MODEL = "embed-english-v3.0"       # 1024 dims
COHERE_EMBED_DIMS  = 1024


class OpenAIEmbedder:
    """OpenAI text-embedding-3-small via the official openai SDK."""

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if not OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY not set in secrets.toml")
            return [[0.0] * OPENAI_EMBED_DIMS] * len(texts)
        try:
            import openai
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            # OpenAI's embeddings endpoint accepts a batch of inputs in one
            # call — much cheaper/faster than one request per chunk.
            resp = client.embeddings.create(model=OPENAI_EMBED_MODEL, input=texts)
            return [item.embedding for item in resp.data]
        except Exception as e:
            logger.error(f"OpenAI embed error: {e}")
            return [[0.0] * OPENAI_EMBED_DIMS] * len(texts)

    def embed_single(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]


class GeminiEmbedder:
    """Gemini text-embedding-004 via the google-genai SDK."""

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if not GOOGLE_API_KEY:
            logger.error("GOOGLE_API_KEY not set in secrets.toml")
            return [[0.0] * GEMINI_EMBED_DIMS] * len(texts)
        try:
            from google import genai
            client = genai.Client(api_key=GOOGLE_API_KEY)
            resp = client.models.embed_content(model=GEMINI_EMBED_MODEL, contents=texts)
            return [e.values for e in resp.embeddings]
        except Exception as e:
            logger.error(f"Gemini embed error: {e}")
            return [[0.0] * GEMINI_EMBED_DIMS] * len(texts)

    def embed_single(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]


class CohereEmbedder:
    """Cohere embed-english-v3.0 via the cohere SDK."""

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if not COHERE_API_KEY:
            logger.error("COHERE_API_KEY not set in secrets.toml")
            return [[0.0] * COHERE_EMBED_DIMS] * len(texts)
        try:
            import cohere
            client = cohere.ClientV2(api_key=COHERE_API_KEY)
            resp = client.embed(texts=texts, model=COHERE_EMBED_MODEL,
                                input_type="search_document", embedding_types=["float"])
            return resp.embeddings.float_
        except Exception as e:
            logger.error(f"Cohere embed error: {e}")
            return [[0.0] * COHERE_EMBED_DIMS] * len(texts)

    def embed_single(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]
