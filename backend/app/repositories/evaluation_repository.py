import threading
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from loguru import logger
from pymongo import DESCENDING
from pymongo.database import Database

from app.database import get_mongodb, EVALUATIONS_COLLECTION


class EvaluationRepository:
    """
    Repository for persisting evaluation benchmark results, comparison metrics,
    and hallucination suppression rates in MongoDB evaluations collection.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._local_records: List[Dict[str, Any]] = []

    def _get_db(self) -> Optional[Database]:
        return get_mongodb()

    def save_evaluation(self, eval_id: str, report_data: Dict[str, Any]) -> None:
        """Save benchmark evaluation run."""
        record = {
            "_id": eval_id,
            "evaluation_id": eval_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **report_data,
        }

        with self._lock:
            self._local_records.append(record)

        db = self._get_db()
        if db is not None:
            try:
                db[EVALUATIONS_COLLECTION].replace_one(
                    {"_id": eval_id},
                    record,
                    upsert=True,
                )
                logger.info(
                    f"Saved evaluation benchmark record '{eval_id}' to MongoDB collection '{EVALUATIONS_COLLECTION}'."
                )
            except Exception as e:
                logger.error(f"Error persisting evaluation to MongoDB: {e}")

    def get_latest_evaluation(self) -> Optional[Dict[str, Any]]:
        """Retrieve the most recent evaluation benchmark."""
        db = self._get_db()
        if db is not None:
            try:
                doc = db[EVALUATIONS_COLLECTION].find_one(sort=[("timestamp", DESCENDING)])
                if doc:
                    doc_dict = dict(doc)
                    doc_dict.pop("_id", None)
                    return doc_dict
            except Exception as e:
                logger.warning(f"Error fetching evaluation from MongoDB: {e}")

        with self._lock:
            if self._local_records:
                return self._local_records[-1]
        return None

    def list_evaluations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List past evaluation benchmark runs."""
        db = self._get_db()
        if db is not None:
            try:
                cursor = db[EVALUATIONS_COLLECTION].find().sort("timestamp", DESCENDING).limit(limit)
                records = []
                for doc in cursor:
                    doc_dict = dict(doc)
                    doc_dict.pop("_id", None)
                    records.append(doc_dict)
                if records:
                    return records
            except Exception as e:
                logger.warning(f"Error querying evaluations from MongoDB: {e}")

        with self._lock:
            return list(reversed(self._local_records))[:limit]


_eval_repo_instance: Optional[EvaluationRepository] = None


def get_evaluation_repository() -> EvaluationRepository:
    """Returns singleton instance of EvaluationRepository."""
    global _eval_repo_instance
    if _eval_repo_instance is None:
        _eval_repo_instance = EvaluationRepository()
    return _eval_repo_instance
