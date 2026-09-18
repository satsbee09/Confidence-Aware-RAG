import threading
from typing import List, Optional, Dict
from loguru import logger
from pymongo import ReplaceOne
from pymongo.database import Database

from app.database import get_mongodb, CHUNKS_COLLECTION
from app.schemas.chunk import Chunk


class ChunkRepository:
    """
    Repository for persisting and retrieving confidence-aware chunks in MongoDB chunks collection.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._local_cache: Dict[str, Chunk] = {}

    def _get_db(self) -> Optional[Database]:
        return get_mongodb()

    def save_chunks(self, chunks: List[Chunk]) -> None:
        """Bulk save or update text chunks in MongoDB."""
        if not chunks:
            return

        with self._lock:
            for c in chunks:
                self._local_cache[c.chunk_id] = c

        db = self._get_db()
        if db is not None:
            try:
                try:
                    ops = [
                        ReplaceOne(
                            {"_id": chunk.chunk_id},
                            {**chunk.model_dump(), "_id": chunk.chunk_id, "document_id": chunk.doc_id},
                            upsert=True,
                        )
                        for chunk in chunks
                    ]
                    db[CHUNKS_COLLECTION].bulk_write(ops, ordered=False)
                except Exception:
                    for chunk in chunks:
                        cdict = chunk.model_dump()
                        cdict["_id"] = chunk.chunk_id
                        cdict["document_id"] = chunk.doc_id
                        db[CHUNKS_COLLECTION].replace_one({"_id": chunk.chunk_id}, cdict, upsert=True)

                logger.info(
                    f"Saved {len(chunks)} chunks to MongoDB collection '{CHUNKS_COLLECTION}'."
                )
            except Exception as e:
                logger.error(f"Error persisting chunks to MongoDB: {e}")

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """Retrieve a specific chunk by its UUID."""
        db = self._get_db()
        if db is not None:
            try:
                doc = db[CHUNKS_COLLECTION].find_one({"_id": chunk_id})
                if doc:
                    cdict = dict(doc)
                    cdict.pop("_id", None)
                    cdict.pop("document_id", None)
                    return Chunk(**cdict)
            except Exception as e:
                logger.warning(f"Error fetching chunk '{chunk_id}' from MongoDB: {e}")

        with self._lock:
            return self._local_cache.get(chunk_id)

    def get_chunks_by_document(self, document_id: str) -> List[Chunk]:
        """Retrieve all chunks belonging to a document."""
        db = self._get_db()
        if db is not None:
            try:
                cursor = db[CHUNKS_COLLECTION].find(
                    {"$or": [{"doc_id": document_id}, {"document_id": document_id}]}
                )
                chunks = []
                for doc in cursor:
                    cdict = dict(doc)
                    cdict.pop("_id", None)
                    cdict.pop("document_id", None)
                    chunks.append(Chunk(**cdict))
                if chunks:
                    return chunks
            except Exception as e:
                logger.warning(f"Error reading chunks from MongoDB: {e}")

        with self._lock:
            return [c for c in self._local_cache.values() if c.doc_id == document_id]

    def delete_chunks_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document."""
        count = 0
        db = self._get_db()
        if db is not None:
            try:
                res = db[CHUNKS_COLLECTION].delete_many(
                    {"$or": [{"doc_id": document_id}, {"document_id": document_id}]}
                )
                count = res.deleted_count
            except Exception as e:
                logger.error(f"Error deleting chunks from MongoDB for doc '{document_id}': {e}")

        with self._lock:
            keys_to_remove = [k for k, c in self._local_cache.items() if c.doc_id == document_id]
            for k in keys_to_remove:
                del self._local_cache[k]

        return count


_chunk_repo_instance: Optional[ChunkRepository] = None


def get_chunk_repository() -> ChunkRepository:
    """Returns singleton instance of ChunkRepository."""
    global _chunk_repo_instance
    if _chunk_repo_instance is None:
        _chunk_repo_instance = ChunkRepository()
    return _chunk_repo_instance
