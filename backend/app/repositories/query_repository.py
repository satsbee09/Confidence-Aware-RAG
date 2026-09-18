import threading
from typing import List, Optional, Dict
from loguru import logger
from pymongo import DESCENDING
from pymongo.database import Database

from app.database import get_mongodb, QUERIES_COLLECTION
from app.schemas.db_models import QueryHistoryRecord


class QueryRepository:
    """
    Repository for persisting natural language queries, LLM answers, risk assessments,
    and latency metrics in MongoDB queries collection.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._history: Dict[str, QueryHistoryRecord] = {}

    def _get_db(self) -> Optional[Database]:
        return get_mongodb()

    def save_query(self, record: QueryHistoryRecord) -> None:
        """Persist executed query record."""
        with self._lock:
            self._history[record.query_id] = record

        db = self._get_db()
        if db is not None:
            try:
                qdict = record.model_dump()
                qdict["_id"] = record.query_id
                db[QUERIES_COLLECTION].replace_one(
                    {"_id": record.query_id},
                    qdict,
                    upsert=True,
                )
                logger.info(
                    f"Saved query record '{record.query_id}' to MongoDB collection '{QUERIES_COLLECTION}'."
                )
            except Exception as e:
                logger.error(f"Error persisting query record to MongoDB: {e}")

    def get_query(self, query_id: str) -> Optional[QueryHistoryRecord]:
        """Retrieve a single query record by ID."""
        db = self._get_db()
        if db is not None:
            try:
                doc = db[QUERIES_COLLECTION].find_one({"_id": query_id})
                if doc:
                    qdict = dict(doc)
                    qdict.pop("_id", None)
                    return QueryHistoryRecord(**qdict)
            except Exception as e:
                logger.warning(f"Error fetching query '{query_id}' from MongoDB: {e}")

        with self._lock:
            return self._history.get(query_id)

    def list_queries(self, limit: int = 50) -> List[QueryHistoryRecord]:
        """List past queries sorted by creation timestamp descending."""
        db = self._get_db()
        if db is not None:
            try:
                cursor = db[QUERIES_COLLECTION].find().sort("created_at", DESCENDING).limit(limit)
                records = []
                for doc in cursor:
                    qdict = dict(doc)
                    qdict.pop("_id", None)
                    records.append(QueryHistoryRecord(**qdict))
                if records:
                    return records
            except Exception as e:
                logger.warning(f"Error listing queries from MongoDB: {e}")

        with self._lock:
            queries = list(self._history.values())
        queries.sort(key=lambda q: q.created_at, reverse=True)
        return queries[:limit]


_query_repo_instance: Optional[QueryRepository] = None


def get_query_repository() -> QueryRepository:
    """Returns singleton instance of QueryRepository."""
    global _query_repo_instance
    if _query_repo_instance is None:
        _query_repo_instance = QueryRepository()
    return _query_repo_instance
