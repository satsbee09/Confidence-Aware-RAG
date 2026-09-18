import threading
from typing import List, Optional, Dict
from loguru import logger
from pymongo import ReplaceOne
from pymongo.database import Database

from app.database import get_mongodb, EVIDENCE_COLLECTION
from app.schemas.db_models import EvidenceHistoryRecord


class EvidenceRepository:
    """
    Repository for persisting and querying supporting evidence items, exact token bounding boxes,
    and optical risk tags in MongoDB evidence collection.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._cache: Dict[str, EvidenceHistoryRecord] = {}

    def _get_db(self) -> Optional[Database]:
        return get_mongodb()

    def save_evidence_items(self, items: List[EvidenceHistoryRecord]) -> None:
        """Bulk save evidence records associated with a query."""
        if not items:
            return

        with self._lock:
            for item in items:
                self._cache[item.evidence_id] = item

        db = self._get_db()
        if db is not None:
            try:
                try:
                    ops = [
                        ReplaceOne({"_id": item.evidence_id}, {**item.model_dump(), "_id": item.evidence_id}, upsert=True)
                        for item in items
                    ]
                    db[EVIDENCE_COLLECTION].bulk_write(ops, ordered=False)
                except Exception:
                    for item in items:
                        edict = item.model_dump()
                        edict["_id"] = item.evidence_id
                        db[EVIDENCE_COLLECTION].replace_one({"_id": item.evidence_id}, edict, upsert=True)

                logger.info(
                    f"Saved {len(items)} evidence records to MongoDB collection '{EVIDENCE_COLLECTION}'."
                )
            except Exception as e:
                logger.error(f"Error persisting evidence items to MongoDB: {e}")

    def get_evidence_by_query(self, query_id: str) -> List[EvidenceHistoryRecord]:
        """Retrieve all evidence items produced for a specific query."""
        db = self._get_db()
        if db is not None:
            try:
                cursor = db[EVIDENCE_COLLECTION].find({"query_id": query_id})
                items = []
                for doc in cursor:
                    edict = dict(doc)
                    edict.pop("_id", None)
                    items.append(EvidenceHistoryRecord(**edict))
                if items:
                    return items
            except Exception as e:
                logger.warning(f"Error querying evidence from MongoDB: {e}")

        with self._lock:
            return [it for it in self._cache.values() if it.query_id == query_id]

    def get_evidence_by_document(self, document_id: str) -> List[EvidenceHistoryRecord]:
        """Retrieve all evidence items for a given document."""
        db = self._get_db()
        if db is not None:
            try:
                cursor = db[EVIDENCE_COLLECTION].find({"document_id": document_id})
                items = []
                for doc in cursor:
                    edict = dict(doc)
                    edict.pop("_id", None)
                    items.append(EvidenceHistoryRecord(**edict))
                if items:
                    return items
            except Exception as e:
                logger.warning(f"Error querying evidence for document '{document_id}': {e}")

        with self._lock:
            return [it for it in self._cache.values() if it.document_id == document_id]


_evidence_repo_instance: Optional[EvidenceRepository] = None


def get_evidence_repository() -> EvidenceRepository:
    """Returns singleton instance of EvidenceRepository."""
    global _evidence_repo_instance
    if _evidence_repo_instance is None:
        _evidence_repo_instance = EvidenceRepository()
    return _evidence_repo_instance
