import threading
from typing import List, Optional, Dict
from loguru import logger
from pymongo import InsertOne, ReplaceOne
from pymongo.database import Database

from app.database import get_mongodb, OCR_TOKENS_COLLECTION
from app.schemas.db_models import OCRTokenRecord
from app.schemas.ocr import OCRWord


class OCRTokenRepository:
    """
    Repository for persisting and querying word-level OCR tokens with bounding boxes
    and confidences in MongoDB ocr_tokens collection.
    """

    def __init__(self):
        self._lock = threading.RLock()
        # In-memory backup: doc_id -> list of tokens
        self._local_cache: Dict[str, List[OCRTokenRecord]] = {}

    def _get_db(self) -> Optional[Database]:
        return get_mongodb()

    def bulk_save_tokens(self, tokens: List[OCRTokenRecord]) -> None:
        """Bulk insert OCR token records into MongoDB."""
        if not tokens:
            return

        doc_id = tokens[0].document_id
        with self._lock:
            if doc_id not in self._local_cache:
                self._local_cache[doc_id] = []
            self._local_cache[doc_id].extend(tokens)

        db = self._get_db()
        if db is not None:
            try:
                try:
                    operations = [
                        ReplaceOne({"_id": t.token_id}, {**t.model_dump(), "_id": t.token_id}, upsert=True)
                        for t in tokens
                    ]
                    db[OCR_TOKENS_COLLECTION].bulk_write(operations, ordered=False)
                except Exception:
                    for t in tokens:
                        tdict = t.model_dump()
                        tdict["_id"] = t.token_id
                        db[OCR_TOKENS_COLLECTION].replace_one({"_id": t.token_id}, tdict, upsert=True)

                logger.info(
                    f"Persisted {len(tokens)} OCR tokens for document '{doc_id}' to MongoDB collection '{OCR_TOKENS_COLLECTION}'."
                )
            except Exception as e:
                logger.error(f"Error bulk saving OCR tokens to MongoDB: {e}")

    def get_tokens_by_page(self, document_id: str, page_number: int) -> List[OCRTokenRecord]:
        """Retrieve all OCR tokens for a given document and page ordered by token_index."""
        db = self._get_db()
        if db is not None:
            try:
                cursor = db[OCR_TOKENS_COLLECTION].find(
                    {"document_id": document_id, "page_number": page_number}
                ).sort("token_index", 1)
                tokens = []
                for doc in cursor:
                    tdict = dict(doc)
                    tdict.pop("_id", None)
                    tokens.append(OCRTokenRecord(**tdict))
                if tokens:
                    return tokens
            except Exception as e:
                logger.warning(f"Error reading OCR tokens from MongoDB: {e}")

        with self._lock:
            doc_tokens = self._local_cache.get(document_id, [])
            matched = [t for t in doc_tokens if t.page_number == page_number]
            matched.sort(key=lambda t: t.token_index)
            return matched

    def get_tokens_by_document(self, document_id: str) -> List[OCRTokenRecord]:
        """Retrieve all OCR tokens for a given document."""
        db = self._get_db()
        if db is not None:
            try:
                cursor = db[OCR_TOKENS_COLLECTION].find({"document_id": document_id}).sort(
                    [("page_number", 1), ("token_index", 1)]
                )
                tokens = []
                for doc in cursor:
                    tdict = dict(doc)
                    tdict.pop("_id", None)
                    tokens.append(OCRTokenRecord(**tdict))
                if tokens:
                    return tokens
            except Exception as e:
                logger.warning(f"Error querying tokens for doc '{document_id}': {e}")

        with self._lock:
            return list(self._local_cache.get(document_id, []))

    def delete_tokens_by_document(self, document_id: str) -> int:
        """Delete all tokens for a document."""
        count = 0
        db = self._get_db()
        if db is not None:
            try:
                res = db[OCR_TOKENS_COLLECTION].delete_many({"document_id": document_id})
                count = res.deleted_count
            except Exception as e:
                logger.error(f"Error deleting tokens from MongoDB for doc '{document_id}': {e}")

        with self._lock:
            if document_id in self._local_cache:
                del self._local_cache[document_id]

        return count


_ocr_token_repo_instance: Optional[OCRTokenRepository] = None


def get_ocr_token_repository() -> OCRTokenRepository:
    """Returns singleton instance of OCRTokenRepository."""
    global _ocr_token_repo_instance
    if _ocr_token_repo_instance is None:
        _ocr_token_repo_instance = OCRTokenRepository()
    return _ocr_token_repo_instance
