import json
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from loguru import logger

from app.core.config import settings
from app.schemas.chunk import Chunk


class BaseVectorStore(ABC):
    """
    Abstract Vector Store Repository Interface.
    Decouples retrieval and vector indexing logic from any specific vendor/library.
    """

    @abstractmethod
    def add_chunks(self, chunks: List[Chunk], embeddings: np.ndarray) -> None:
        """Add chunks and their corresponding embedding vectors to index."""
        pass

    @abstractmethod
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = settings.TOP_K,
        doc_id: Optional[str] = None,
    ) -> List[Tuple[Chunk, float]]:
        """Search nearest chunks returning pairs of (Chunk, CosineSimilarity)."""
        pass

    @abstractmethod
    def delete_document(self, doc_id: str) -> bool:
        """Delete all chunks and vectors associated with a document ID."""
        pass

    @abstractmethod
    def get_document_chunks(self, doc_id: str) -> List[Chunk]:
        """Retrieve all stored chunks for a given document."""
        pass

    @abstractmethod
    def list_documents(self) -> List[str]:
        """List all unique document IDs indexed in vector store."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Total number of indexed vectors."""
        pass

    @abstractmethod
    def save_to_disk(self, directory: Optional[Path] = None) -> None:
        """Persist vector index and metadata to disk."""
        pass

    @abstractmethod
    def load_from_disk(self, directory: Optional[Path] = None) -> bool:
        """Load vector index and metadata from disk."""
        pass


class NumpyVectorStore(BaseVectorStore):
    """
    High-performance, pure NumPy vector store computing exact Cosine Similarity
    via matrix-vector inner products. Zero external C++ DLL dependencies,
    ensuring 100% cross-platform reliability on Windows, macOS, and Linux.
    """

    def __init__(self, dimension: int = 384, storage_dir: Optional[Path] = None):
        self.dimension = dimension
        self.storage_dir = storage_dir or settings.STORAGE_DIR
        self._lock = threading.Lock()

        # Internal in-memory storage
        self.vectors: np.ndarray = np.empty((0, self.dimension), dtype=np.float32)
        self.chunks: List[Chunk] = []
        self.doc_to_indices: Dict[str, List[int]] = {}

        # Auto-load existing index if available
        self.load_from_disk()

    def add_chunks(self, chunks: List[Chunk], embeddings: np.ndarray) -> None:
        if len(chunks) == 0:
            return

        if embeddings.shape[0] != len(chunks):
            raise ValueError(
                f"Embedding count ({embeddings.shape[0]}) does not match chunk count ({len(chunks)})"
            )

        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Embedding dimension ({embeddings.shape[1]}) does not match index dimension ({self.dimension})"
            )

        vectors = embeddings.astype(np.float32)

        with self._lock:
            start_idx = len(self.chunks)
            if self.vectors.shape[0] == 0:
                self.vectors = vectors
            else:
                self.vectors = np.vstack([self.vectors, vectors])

            for i, chunk in enumerate(chunks):
                idx = start_idx + i
                self.chunks.append(chunk)
                if chunk.doc_id not in self.doc_to_indices:
                    self.doc_to_indices[chunk.doc_id] = []
                self.doc_to_indices[chunk.doc_id].append(idx)

            logger.info(
                f"Indexed {len(chunks)} chunks in NumpyVectorStore for doc_id '{chunks[0].doc_id}'. "
                f"Total vectors: {len(self.chunks)}"
            )

        self.save_to_disk()

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = settings.TOP_K,
        doc_id: Optional[str] = None,
    ) -> List[Tuple[Chunk, float]]:
        with self._lock:
            total = len(self.chunks)
            if total == 0:
                logger.warning("Search called on empty vector store.")
                return []

            q_vec = query_embedding.flatten().astype(np.float32)
            # Cosine similarity via inner product on normalized vectors: shape (N,)
            scores = np.dot(self.vectors, q_vec)

            # Determine candidate indices
            if doc_id:
                candidate_indices = self.doc_to_indices.get(doc_id, [])
                if not candidate_indices:
                    return []
            else:
                candidate_indices = list(range(total))

            candidate_scores = scores[candidate_indices]
            # Get top_k sorted descending
            sorted_local_ranks = np.argsort(-candidate_scores)[:top_k]

            results: List[Tuple[Chunk, float]] = []
            for local_rank in sorted_local_ranks:
                global_idx = candidate_indices[local_rank]
                sim = float(max(-1.0, min(1.0, candidate_scores[local_rank])))
                results.append((self.chunks[global_idx], round(sim, 4)))

            return results

    def delete_document(self, doc_id: str) -> bool:
        with self._lock:
            if doc_id not in self.doc_to_indices:
                logger.warning(f"Attempted to delete non-existent doc_id: {doc_id}")
                return False

            ids_to_remove = set(self.doc_to_indices[doc_id])
            retained_chunks = [c for i, c in enumerate(self.chunks) if i not in ids_to_remove]
            retained_vectors = [v for i, v in enumerate(self.vectors) if i not in ids_to_remove]

            self.chunks = retained_chunks
            self.vectors = (
                np.array(retained_vectors, dtype=np.float32)
                if retained_vectors
                else np.empty((0, self.dimension), dtype=np.float32)
            )

            # Rebuild doc_to_indices
            self.doc_to_indices = {}
            for i, chunk in enumerate(self.chunks):
                if chunk.doc_id not in self.doc_to_indices:
                    self.doc_to_indices[chunk.doc_id] = []
                self.doc_to_indices[chunk.doc_id].append(i)

            logger.info(f"Deleted document '{doc_id}'. Remaining vectors: {len(self.chunks)}")

        self.save_to_disk()
        return True

    def get_document_chunks(self, doc_id: str) -> List[Chunk]:
        with self._lock:
            if doc_id not in self.doc_to_indices:
                return []
            return [self.chunks[idx] for idx in self.doc_to_indices[doc_id]]

    def list_documents(self) -> List[str]:
        with self._lock:
            return list(self.doc_to_indices.keys())

    def count(self) -> int:
        return len(self.chunks)

    def save_to_disk(self, directory: Optional[Path] = None) -> None:
        target_dir = directory or self.storage_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        vec_file = target_dir / "vectors.npz"
        meta_file = target_dir / "chunks_metadata.json"

        with self._lock:
            np.savez_compressed(vec_file, vectors=self.vectors)
            chunks_data = [chunk.model_dump() for chunk in self.chunks]
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "dimension": self.dimension,
                        "doc_to_indices": self.doc_to_indices,
                        "chunks": chunks_data,
                    },
                    f,
                    indent=2,
                )
        logger.debug(f"Saved {len(self.chunks)} vectors to {target_dir}")

    def load_from_disk(self, directory: Optional[Path] = None) -> bool:
        target_dir = directory or self.storage_dir
        vec_file = target_dir / "vectors.npz"
        meta_file = target_dir / "chunks_metadata.json"

        if not vec_file.exists() or not meta_file.exists():
            return False

        try:
            with self._lock:
                npz_data = np.load(vec_file)
                self.vectors = npz_data["vectors"]
                with open(meta_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.doc_to_indices = {
                    k: list(v) for k, v in data.get("doc_to_indices", {}).items()
                }
                self.chunks = [Chunk(**c) for c in data.get("chunks", [])]

            logger.info(f"Loaded {len(self.chunks)} vectors from {target_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to load vector store from {target_dir}: {e}")
            return False


# Singleton Vector Store provider
_vector_store_instance: Optional[BaseVectorStore] = None

def get_vector_store(storage_dir: Optional[Path] = None, reset: bool = False) -> BaseVectorStore:
    """Returns singleton instance of the VectorStore, re-initializing if storage path changes."""
    global _vector_store_instance
    target_dir = storage_dir or settings.STORAGE_DIR
    if _vector_store_instance is None or reset or _vector_store_instance.storage_dir != target_dir:
        _vector_store_instance = NumpyVectorStore(storage_dir=target_dir)
    return _vector_store_instance

