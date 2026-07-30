"""embeddings/multilingual_embeddings.py — Multilingual embedders (Hindi, Telugu, English)."""
import utils.model_cache  # noqa: F401 — sets HF_HOME etc. (this file previously set NONE of this,
                           # so it could silently download models to a different default cache dir)

from typing import List
from utils.logger import get_logger
from utils.device import get_device
from utils.timing import timed
logger = get_logger(__name__)
MODEL_MAP = {
    "multilingual-e5":"intfloat/multilingual-e5-base",
    "multilingual_e5":"intfloat/multilingual-e5-base",
    "bge-m3":"BAAI/bge-m3","bge_m3":"BAAI/bge-m3",
    "labse":"sentence-transformers/LaBSE",
}

# Module-level cache so the model is loaded ONCE per process, not once per
# EmbeddingFactory() call (previously every _build_indexes() run created a
# fresh MultilingualEmbedder and reloaded the full model from scratch).
_MODEL_CACHE = {}


class MultilingualEmbedder:
    def __init__(self, model_name: str = "multilingual-e5"):
        self.model_id = MODEL_MAP.get(model_name.lower(), model_name)

    def _load(self):
        if self.model_id not in _MODEL_CACHE:
            from sentence_transformers import SentenceTransformer
            device = get_device()
            with timed(f"load_model[{self.model_id}]"):
                _MODEL_CACHE[self.model_id] = SentenceTransformer(self.model_id, device=device)
            logger.info(f"Loaded multilingual: {self.model_id} on device={device}")
        return _MODEL_CACHE[self.model_id]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts: return []
        try:
            model = self._load()
            if "multilingual-e5" in self.model_id:
                texts = [f"passage: {t}" for t in texts]
            with timed(f"embed.batch[{len(texts)} chunks]"):
                return model.encode(texts, show_progress_bar=False, convert_to_numpy=True).tolist()
        except Exception as e:
            logger.error(f"Multilingual embed: {e}"); return [[0.0]*768]*len(texts)

    def embed_single(self, text): return self.embed_batch([text])[0]

    def embed_query(self, text):
        model = self._load()
        try:
            if "multilingual-e5" in self.model_id: text = f"query: {text}"
            return model.encode([text], show_progress_bar=False, convert_to_numpy=True)[0].tolist()
        except Exception as e:
            logger.error(f"Query embed: {e}"); return [0.0]*768
