import threading
from typing import List, Optional, Dict
from loguru import logger
from pymongo.database import Database

from app.database import get_mongodb, PAGES_COLLECTION
from app.schemas.page import PageSummary


class PageRepository:
    """
    Repository for persisting and retrieving page dimensions and metadata in MongoDB pages collection.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._local_cache: Dict[str, PageSummary] = {}

    def _get_db(self) -> Optional[Database]:
        return get_mongodb()

    def save_pages(self, pages: List[PageSummary]) -> None:
        """Bulk save or update page records."""
        if not pages:
            return

        with self._lock:
            for p in pages:
                self._local_cache[p.page_id] = p

        db = self._get_db()
        if db is not None:
            try:
                for page in pages:
                    doc_dict = page.model_dump()
                    doc_dict["_id"] = page.page_id
                    db[PAGES_COLLECTION].replace_one(
                        {"_id": page.page_id},
                        doc_dict,
                        upsert=True,
                    )
                logger.info(f"Saved {len(pages)} pages to MongoDB collection '{PAGES_COLLECTION}'.")
            except Exception as e:
                logger.error(f"Error persisting pages to MongoDB: {e}")

    def get_page(self, document_id: str, page_number: int) -> Optional[PageSummary]:
        """Retrieve page metadata for a specific document and page number."""
        page_id = f"{document_id}_page_{page_number}"

        db = self._get_db()
        if db is not None:
            try:
                doc = db[PAGES_COLLECTION].find_one(
                    {"document_id": document_id, "page_number": page_number}
                )
                if doc:
                    doc_dict = dict(doc)
                    doc_dict.pop("_id", None)
                    return PageSummary(**doc_dict)
            except Exception as e:
                logger.warning(f"Error querying page from MongoDB: {e}")

        with self._lock:
            return self._local_cache.get(page_id)

    def list_pages_by_document(self, document_id: str) -> List[PageSummary]:
        """List all pages for a given document sorted by page number ascending."""
        db = self._get_db()
        if db is not None:
            try:
                cursor = db[PAGES_COLLECTION].find({"document_id": document_id}).sort("page_number", 1)
                pages = []
                for doc in cursor:
                    doc_dict = dict(doc)
                    doc_dict.pop("_id", None)
                    pages.append(PageSummary(**doc_dict))
                if pages:
                    return pages
            except Exception as e:
                logger.warning(f"Error listing pages from MongoDB: {e}")

        with self._lock:
            matched = [p for p in self._local_cache.values() if p.document_id == document_id]
            matched.sort(key=lambda p: p.page_number)
            return matched

    def delete_pages_by_document(self, document_id: str) -> int:
        """Delete all page records belonging to a document."""
        count = 0
        db = self._get_db()
        if db is not None:
            try:
                res = db[PAGES_COLLECTION].delete_many({"document_id": document_id})
                count = res.deleted_count
            except Exception as e:
                logger.error(f"Error deleting pages from MongoDB for doc '{document_id}': {e}")

        with self._lock:
            keys_to_remove = [k for k, p in self._local_cache.items() if p.document_id == document_id]
            for k in keys_to_remove:
                del self._local_cache[k]

        return count


_page_repo_instance: Optional[PageRepository] = None


def get_page_repository() -> PageRepository:
    """Returns singleton instance of PageRepository."""
    global _page_repo_instance
    if _page_repo_instance is None:
        _page_repo_instance = PageRepository()
    return _page_repo_instance
