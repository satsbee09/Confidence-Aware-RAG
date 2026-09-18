from app.database.mongodb import mongodb_manager, get_mongodb
from app.database.collections import (
    DOCUMENTS_COLLECTION,
    PAGES_COLLECTION,
    OCR_TOKENS_COLLECTION,
    CHUNKS_COLLECTION,
    QUERIES_COLLECTION,
    EVIDENCE_COLLECTION,
    EVALUATIONS_COLLECTION,
)
from app.database.indexes import create_indexes

__all__ = [
    "mongodb_manager",
    "get_mongodb",
    "create_indexes",
    "DOCUMENTS_COLLECTION",
    "PAGES_COLLECTION",
    "OCR_TOKENS_COLLECTION",
    "CHUNKS_COLLECTION",
    "QUERIES_COLLECTION",
    "EVIDENCE_COLLECTION",
    "EVALUATIONS_COLLECTION",
]
