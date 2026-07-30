"""embeddings/embedding_factory.py — Returns the right embedder for the selected model."""
from utils.logger import get_logger
logger = get_logger(__name__)


class EmbeddingFactory:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name

    def get_embedder(self):
        name = self.model_name.lower()
        if name.startswith("openai"):
            from embeddings.openai_embeddings import OpenAIEmbedder;  return OpenAIEmbedder()
        if name.startswith("gemini"):
            from embeddings.openai_embeddings import GeminiEmbedder;  return GeminiEmbedder()
        if name.startswith("jina"):
            from embeddings.jina_embeddings   import JinaEmbedder;    return JinaEmbedder()
        if name.startswith("cohere"):
            from embeddings.openai_embeddings import CohereEmbedder;  return CohereEmbedder()
        if any(k in name for k in ["multilingual-e5", "multilingual_e5", "bge-m3", "bge_m3", "labse"]):
            from embeddings.multilingual_embeddings import MultilingualEmbedder
            return MultilingualEmbedder(self.model_name)
        from embeddings.local_embeddings import LocalEmbedder
        return LocalEmbedder(self.model_name)