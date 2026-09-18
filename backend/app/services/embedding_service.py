import numpy as np
from abc import ABC, abstractmethod
from typing import List, Union, Optional
from loguru import logger

from app.core.config import settings


class BaseEmbeddingService(ABC):
    """
    Abstract Interface for Embedding Services.
    Allows seamlessly swapping embedding backends (SentenceTransformers, OpenAI, FastEmbed).
    """

    @abstractmethod
    def encode_text(self, text: str) -> np.ndarray:
        """Encode a single text into a 1D normalized numpy embedding."""
        pass

    @abstractmethod
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """Encode a batch of texts into a 2D normalized numpy array (N, D)."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Returns the embedding vector dimension."""
        pass


class SentenceTransformerEmbeddingService(BaseEmbeddingService):
    """
    Sentence Transformers Embedding Provider.
    Implements singleton model loading to prevent redundant model instantiation.
    """

    _instance: Optional["SentenceTransformerEmbeddingService"] = None
    _model = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SentenceTransformerEmbeddingService, cls).__new__(cls)
        return cls._instance

    def __init__(
        self,
        model_name: str = settings.EMBEDDING_MODEL_NAME,
        device: str = settings.DEVICE,
        batch_size: int = settings.EMBEDDING_BATCH_SIZE,
    ):
        if self._model is None:
            self.model_name = model_name
            self.device = device
            self.batch_size = batch_size
            self._load_model()

    def _load_model(self) -> None:
        """Loads the sentence transformer model into memory once."""
        from sentence_transformers import SentenceTransformer

        logger.info(f"Loading embedding model '{self.model_name}' on device '{self.device}'...")
        self._model = SentenceTransformer(self.model_name, device=self.device)
        if hasattr(self._model, "get_embedding_dimension"):
            self._dimension = self._model.get_embedding_dimension()
        elif hasattr(self._model, "get_sentence_embedding_dimension"):
            self._dimension = self._model.get_sentence_embedding_dimension()
        else:
            self._dimension = 384
        logger.info(f"Embedding model loaded successfully. Embedding dimension: {self._dimension}")

    @property
    def dimension(self) -> int:
        return self._dimension

    def encode_text(self, text: str) -> np.ndarray:
        """
        Encode a single string and return a normalized 1D float32 vector.
        """
        if not text.strip():
            # Return zero vector if string is empty
            return np.zeros((self.dimension,), dtype=np.float32)

        embedding = self._model.encode(
            text,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,  # L2 normalize for cosine similarity
        )
        return embedding.astype(np.float32)

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        Encode a list of strings into a 2D normalized float32 array (N, D).
        """
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        # Replace empty strings with single space to avoid tokenizer errors
        sanitized_texts = [t if t.strip() else " " for t in texts]

        embeddings = self._model.encode(
            sanitized_texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,  # L2 normalize for cosine similarity
        )
        return embeddings.astype(np.float32)


# Global singleton instance provider
_embedding_service_instance: Optional[BaseEmbeddingService] = None


def get_embedding_service() -> BaseEmbeddingService:
    """Returns the singleton embedding service instance."""
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = SentenceTransformerEmbeddingService()
    return _embedding_service_instance
