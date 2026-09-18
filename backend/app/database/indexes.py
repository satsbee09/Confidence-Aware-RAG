from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database
from loguru import logger

from app.database.collections import (
    DOCUMENTS_COLLECTION,
    PAGES_COLLECTION,
    OCR_TOKENS_COLLECTION,
    CHUNKS_COLLECTION,
    QUERIES_COLLECTION,
    EVIDENCE_COLLECTION,
    EVALUATIONS_COLLECTION,
)


def create_indexes(db: Database) -> None:
    """
    Create optimized MongoDB compound indexes for frequently queried fields
    supporting high-speed token lookups, evidence traces, and query history.
    """
    try:
        logger.info("Ensuring MongoDB collection indexes...")

        # 1. Documents Collection
        db[DOCUMENTS_COLLECTION].create_index([("created_at", DESCENDING)], name="idx_docs_created_at")
        db[DOCUMENTS_COLLECTION].create_index([("filename", ASCENDING)], name="idx_docs_filename")

        # 2. Pages Collection
        db[PAGES_COLLECTION].create_index(
            [("document_id", ASCENDING), ("page_number", ASCENDING)],
            unique=True,
            name="idx_pages_doc_page",
        )

        # 3. OCR Tokens Collection
        db[OCR_TOKENS_COLLECTION].create_index(
            [("document_id", ASCENDING), ("page_number", ASCENDING)],
            name="idx_tokens_doc_page",
        )
        db[OCR_TOKENS_COLLECTION].create_index(
            [("document_id", ASCENDING), ("page_number", ASCENDING), ("token_index", ASCENDING)],
            name="idx_tokens_doc_page_idx",
        )

        # 4. Chunks Collection
        db[CHUNKS_COLLECTION].create_index([("document_id", ASCENDING)], name="idx_chunks_doc_id")
        db[CHUNKS_COLLECTION].create_index([("chunk_id", ASCENDING)], unique=True, name="idx_chunks_chunk_id")

        # 5. Queries Collection
        db[QUERIES_COLLECTION].create_index([("created_at", DESCENDING)], name="idx_queries_created_at")

        # 6. Evidence Collection
        db[EVIDENCE_COLLECTION].create_index([("query_id", ASCENDING)], name="idx_evidence_query_id")
        db[EVIDENCE_COLLECTION].create_index(
            [("document_id", ASCENDING), ("page_number", ASCENDING)],
            name="idx_evidence_doc_page",
        )

        # 7. Evaluations Collection
        db[EVALUATIONS_COLLECTION].create_index([("created_at", DESCENDING)], name="idx_evaluations_created_at")

        logger.info("MongoDB indexes verified successfully.")
    except Exception as e:
        logger.warning(f"Note on MongoDB index creation: {e}")
