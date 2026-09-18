import json
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any
from loguru import logger

from app.core.config import settings
from app.schemas.document import DocumentSummary
from app.database import get_mongodb, DOCUMENTS_COLLECTION


class DocumentRepository:
    """
    Repository for persisting and managing document metadata in MongoDB Atlas
    with local disk fallback for offline resilience.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or settings.STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.storage_dir / "documents_registry.json"
        self._lock = threading.RLock()
        self._registry: Dict[str, DocumentSummary] = {}
        self._load_registry()

    def _get_db(self):
        return get_mongodb()

    def _load_registry(self) -> None:
        """Load document summaries from disk cache."""
        if not self.registry_file.exists():
            return

        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._registry = {k: DocumentSummary(**v) for k, v in data.items()}
            logger.info(f"Loaded {len(self._registry)} documents from local registry cache.")
        except Exception as e:
            logger.error(f"Error loading local document registry from {self.registry_file}: {e}")

    def _save_registry(self) -> None:
        """Persist document summaries to disk cache."""
        with self._lock:
            data = {k: v.model_dump() for k, v in self._registry.items()}
            try:
                with open(self.registry_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                logger.warning(f"Failed to update local registry cache: {e}")

    def save_document(self, summary: DocumentSummary) -> None:
        """Save or update document summary in MongoDB and local cache."""
        # 1. Update in memory and local disk
        with self._lock:
            self._registry[summary.document_id] = summary
        self._save_registry()

        # 2. Persist to MongoDB
        db = self._get_db()
        if db is not None:
            try:
                doc_dict = summary.model_dump()
                doc_dict["_id"] = summary.document_id
                db[DOCUMENTS_COLLECTION].replace_one(
                    {"_id": summary.document_id},
                    doc_dict,
                    upsert=True,
                )
                logger.info(
                    f"Saved document '{summary.filename}' (ID: {summary.document_id}) to MongoDB collection '{DOCUMENTS_COLLECTION}'."
                )
            except Exception as e:
                logger.error(f"Error persisting document to MongoDB: {e}")

    def list_documents(self) -> List[DocumentSummary]:
        """Return all registered documents sorted by creation date descending."""
        db = self._get_db()
        if db is not None:
            try:
                cursor = db[DOCUMENTS_COLLECTION].find().sort("created_at", -1)
                docs: List[DocumentSummary] = []
                for item in cursor:
                    # Strip MongoDB _id if needed
                    item_dict = dict(item)
                    if "_id" in item_dict and "document_id" not in item_dict:
                        item_dict["document_id"] = str(item_dict["_id"])
                    item_dict.pop("_id", None)
                    docs.append(DocumentSummary(**item_dict))
                if docs:
                    with self._lock:
                        for d in docs:
                            self._registry[d.document_id] = d
                    return docs
            except Exception as e:
                logger.warning(f"Failed to read documents from MongoDB, falling back to local registry: {e}")

        with self._lock:
            docs = list(self._registry.values())
        docs.sort(key=lambda d: d.created_at, reverse=True)
        return docs

    def get_document(self, doc_id: str) -> Optional[DocumentSummary]:
        """Retrieve a specific document summary by ID with fast local cache hit."""
        with self._lock:
            if doc_id in self._registry:
                return self._registry[doc_id]

        db = self._get_db()
        if db is not None:
            try:
                item = db[DOCUMENTS_COLLECTION].find_one({"_id": doc_id})
                if item:
                    item_dict = dict(item)
                    item_dict.pop("_id", None)
                    doc = DocumentSummary(**item_dict)
                    with self._lock:
                        self._registry[doc_id] = doc
                    return doc
            except Exception as e:
                logger.warning(f"Error querying MongoDB for doc '{doc_id}': {e}")

        with self._lock:
            return self._registry.get(doc_id)

    def delete_document(self, doc_id: str) -> bool:
        """Delete document from MongoDB and local registry."""
        deleted = False
        db = self._get_db()
        if db is not None:
            try:
                res = db[DOCUMENTS_COLLECTION].delete_one({"_id": doc_id})
                if res.deleted_count > 0:
                    deleted = True
            except Exception as e:
                logger.error(f"Error deleting document '{doc_id}' from MongoDB: {e}")

        with self._lock:
            if doc_id in self._registry:
                del self._registry[doc_id]
                self._save_registry()
                deleted = True

        if deleted:
            logger.info(f"Deleted document '{doc_id}' from repository.")
        return deleted


_document_repo_instance: Optional[DocumentRepository] = None


def get_document_repository(storage_dir: Optional[Path] = None, reset: bool = False) -> DocumentRepository:
    """Returns singleton instance of DocumentRepository, re-initializing if storage path changes."""
    global _document_repo_instance
    target_dir = Path(storage_dir or settings.STORAGE_DIR).resolve()
    if _document_repo_instance is None or reset or _document_repo_instance.storage_dir.resolve() != target_dir:
        _document_repo_instance = DocumentRepository(storage_dir=target_dir)
    return _document_repo_instance
