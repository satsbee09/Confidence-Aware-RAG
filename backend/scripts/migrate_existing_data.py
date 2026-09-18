"""
Migration & Import Utility for Confidence-Aware RAG.
Imports existing JSON registry, chunks metadata, and evaluation results into MongoDB Atlas.
"""

import sys
import os
import json
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from loguru import logger
from app.core.config import settings
from app.database import (
    mongodb_manager,
    create_indexes,
    DOCUMENTS_COLLECTION,
    PAGES_COLLECTION,
    OCR_TOKENS_COLLECTION,
    CHUNKS_COLLECTION,
    EVALUATIONS_COLLECTION,
)


def migrate_data():
    logger.info("Starting MongoDB data migration...")
    logger.info(f"Target Database: '{settings.MONGODB_DATABASE}' at '{settings.MONGODB_URI}'")

    connected = mongodb_manager.connect()
    if not connected:
        logger.error("Could not connect to MongoDB. Please check your MONGODB_URI configuration.")
        return False

    db = mongodb_manager.get_database()
    if db is None:
        logger.error("Database handle is None.")
        return False

    # Ensure indexes
    create_indexes(db)

    storage_dir = settings.STORAGE_DIR

    # 1. Migrate Documents Registry
    registry_file = storage_dir / "documents_registry.json"
    doc_count = 0
    if registry_file.exists():
        try:
            with open(registry_file, "r", encoding="utf-8") as f:
                registry_data = json.load(f)

            for doc_id, doc_info in registry_data.items():
                doc_record = dict(doc_info)
                doc_record["_id"] = doc_id
                db[DOCUMENTS_COLLECTION].replace_one({"_id": doc_id}, doc_record, upsert=True)
                doc_count += 1
            logger.info(f"Successfully migrated {doc_count} documents from {registry_file}.")
        except Exception as e:
            logger.error(f"Error migrating documents registry: {e}")
    else:
        logger.info(f"No existing documents registry found at {registry_file}.")

    # 2. Migrate Chunks & Synthesize Page/Token Records if missing
    chunks_file = storage_dir / "chunks_metadata.json"
    chunk_count = 0
    token_count = 0
    page_set = set()

    if chunks_file.exists():
        try:
            with open(chunks_file, "r", encoding="utf-8") as f:
                chunks_data = json.load(f)

            raw_chunks = chunks_data.get("chunks", [])
            for chunk_dict in raw_chunks:
                c_id = chunk_dict.get("chunk_id")
                d_id = chunk_dict.get("doc_id")
                page_num = chunk_dict.get("page", 1)

                if c_id:
                    c_record = dict(chunk_dict)
                    c_record["_id"] = c_id
                    db[CHUNKS_COLLECTION].replace_one({"_id": c_id}, c_record, upsert=True)
                    chunk_count += 1

                # Page provenance
                if d_id and page_num:
                    page_key = (d_id, page_num)
                    if page_key not in page_set:
                        page_set.add(page_key)
                        page_id = f"{d_id}_page_{page_num}"
                        page_record = {
                            "_id": page_id,
                            "page_id": page_id,
                            "document_id": d_id,
                            "page_number": page_num,
                            "ocr_confidence": chunk_dict.get("raw_confidence", 1.0),
                            "width": chunk_dict.get("page_width", 595.0),
                            "height": chunk_dict.get("page_height", 842.0),
                        }
                        db[PAGES_COLLECTION].replace_one({"_id": page_id}, page_record, upsert=True)

                # Token records from words
                words = chunk_dict.get("words", [])
                for t_idx, w in enumerate(words):
                    token_id = f"{d_id}_p{page_num}_t{t_idx}_{c_id[:6]}"
                    tok_record = {
                        "_id": token_id,
                        "token_id": token_id,
                        "document_id": d_id,
                        "page_number": page_num,
                        "token_index": t_idx,
                        "text": w.get("text", ""),
                        "confidence": w.get("confidence", 1.0),
                        "bbox": w.get("bbox", [0.0, 0.0, 0.0, 0.0]),
                        "line_number": w.get("line_number"),
                    }
                    db[OCR_TOKENS_COLLECTION].replace_one({"_id": token_id}, tok_record, upsert=True)
                    token_count += 1

            logger.info(
                f"Successfully migrated {chunk_count} chunks, {len(page_set)} pages, and {token_count} OCR tokens."
            )
        except Exception as e:
            logger.error(f"Error migrating chunks: {e}")
    else:
        logger.info(f"No existing chunks metadata found at {chunks_file}.")

    # 3. Migrate Evaluation Results
    eval_file = settings.BASE_DIR / "evaluation" / "evaluation_results.json"
    if not eval_file.exists():
        eval_file = Path("evaluation_results.json")

    if eval_file.exists():
        try:
            with open(eval_file, "r", encoding="utf-8") as f:
                eval_data = json.load(f)
            eval_id = "eval_benchmark_latest"
            db[EVALUATIONS_COLLECTION].replace_one(
                {"_id": eval_id},
                {"_id": eval_id, "evaluation_id": eval_id, **eval_data},
                upsert=True,
            )
            logger.info(f"Successfully migrated evaluation benchmark results from {eval_file}.")
        except Exception as e:
            logger.warning(f"Note on evaluation migration: {e}")

    logger.info("Migration completed successfully!")
    return True


if __name__ == "__main__":
    migrate_data()
