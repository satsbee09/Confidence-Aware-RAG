import os
import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from loguru import logger

from app.core.config import settings
from app.schemas.document import DocumentIngestResponse, DocumentSummary
from app.schemas.page import PageSummary
from app.schemas.db_models import OCRTokenRecord
from app.services.ocr_service import OCRService
from app.services.chunking_service import ConfidenceAwareChunker
from app.services.embedding_service import get_embedding_service
from app.repositories import (
    get_vector_store,
    get_document_repository,
    get_page_repository,
    get_ocr_token_repository,
    get_chunk_repository,
)

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}


@router.post(
    "/ingest",
    response_model=DocumentIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest and Index Scanned Document",
    description=(
        "Upload a scanned legal/government PDF or image. Runs OCR with confidence extraction, "
        "persists document, pages, tokens, and chunks into MongoDB Atlas, computes dense embeddings, "
        "and stores in the vector index."
    ),
)
async def ingest_document(file: UploadFile = File(...)) -> DocumentIngestResponse:
    """
    Ingest a PDF or image file through the full confidence-aware pipeline:
    Upload -> Save File -> OCR + Confidence -> Persist Pages & Tokens (MongoDB) ->
    Confidence-Aware Chunking -> Persist Chunks (MongoDB) -> Embeddings -> Vector Index -> Document (MongoDB).
    """
    # 1. Validate file extension
    original_filename = file.filename or "uploaded_document"
    file_ext = Path(original_filename).suffix.lower()

    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file format '{file_ext}'. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    # 2. Generate unique document ID and destination path
    doc_id = str(uuid.uuid4())
    safe_filename = f"{doc_id}_{Path(original_filename).name}"
    save_path = settings.UPLOAD_DIR / safe_filename

    # 3. Read upload file to disk and validate size
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    try:
        content = await file.read()
        total_bytes = len(content)
        if total_bytes > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
            )
        with open(save_path, "wb") as buffer:
            buffer.write(content)
    except HTTPException:
        if save_path.exists():
            save_path.unlink()
        raise
    except Exception as e:
        if save_path.exists():
            save_path.unlink()
        logger.error(f"Failed to save uploaded file '{original_filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save upload on server: {str(e)}",
        )

    logger.info(f"File '{original_filename}' saved ({total_bytes} bytes) as '{save_path}'")

    # 4. Run OCR extraction with word-level confidence
    try:
        ocr_service = OCRService()
        if file_ext == ".pdf":
            ocr_doc = ocr_service.process_pdf(file_path=save_path, doc_id=doc_id)
        else:
            ocr_doc = ocr_service.process_image(file_path=save_path, doc_id=doc_id)
    except Exception as ocr_err:
        logger.error(f"OCR processing failed for '{original_filename}': {ocr_err}")
        if save_path.exists():
            save_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"OCR engine could not process document: {str(ocr_err)}",
        )

    # 5. Persist Pages and OCR Tokens into MongoDB
    try:
        page_repo = get_page_repository()
        token_repo = get_ocr_token_repository()

        page_records = []
        token_records = []

        for p in ocr_doc.pages:
            page_rec = PageSummary(
                page_id=f"{doc_id}_page_{p.page}",
                document_id=doc_id,
                page_number=p.page,
                image_path=f"storage/pages/{doc_id}/page_{p.page}.png",
                width=float(p.width) if p.width else 595.0,
                height=float(p.height) if p.height else 842.0,
                ocr_confidence=p.average_confidence,
                token_count=len(p.words),
                text_preview=p.text[:200] if p.text else "",
            )
            page_records.append(page_rec)

            for token_idx, w in enumerate(p.words):
                tok_rec = OCRTokenRecord(
                    token_id=f"{doc_id}_p{p.page}_t{token_idx}",
                    document_id=doc_id,
                    page_number=p.page,
                    token_index=token_idx,
                    text=w.text,
                    confidence=w.confidence,
                    bbox=w.bbox,
                    line_number=w.line_number,
                )
                token_records.append(tok_rec)

        page_repo.save_pages(page_records)
        token_repo.bulk_save_tokens(token_records)
    except Exception as page_tok_err:
        logger.warning(f"Note persisting pages/tokens to MongoDB: {page_tok_err}")

    # 6. Perform confidence-aware chunking & Persist Chunks in MongoDB
    try:
        chunker = ConfidenceAwareChunker()
        chunks = chunker.create_chunks(ocr_doc)

        chunk_repo = get_chunk_repository()
        chunk_repo.save_chunks(chunks)
    except Exception as chunk_err:
        logger.error(f"Chunking failed for doc '{doc_id}': {chunk_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating text chunks: {str(chunk_err)}",
        )

    # 7. Generate embeddings and index in vector store
    try:
        if chunks:
            embedding_svc = get_embedding_service()
            chunk_texts = [c.chunk_text for c in chunks]
            embeddings = embedding_svc.encode_batch(chunk_texts)

            vector_store = get_vector_store()
            vector_store.add_chunks(chunks, embeddings)
        else:
            logger.warning(f"Document '{doc_id}' produced 0 chunks (empty document).")
    except Exception as idx_err:
        logger.error(f"Vector indexing failed for doc '{doc_id}': {idx_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate embeddings and index vectors: {str(idx_err)}",
        )

    # 8. Record document summary in MongoDB Document Repository
    doc_summary = DocumentSummary(
        document_id=doc_id,
        filename=original_filename,
        pages=ocr_doc.total_pages,
        chunks=len(chunks),
        average_confidence=ocr_doc.average_confidence,
        min_confidence=ocr_doc.min_confidence,
        file_size_bytes=total_bytes,
        metadata={
            "engine": type(ocr_service.engine).__name__,
            "saved_file": str(save_path),
            "status": "processed",
        },
    )
    doc_repo = get_document_repository()
    doc_repo.save_document(doc_summary)

    logger.info(
        f"Ingestion successful for '{original_filename}' (ID: {doc_id}). "
        f"Pages: {ocr_doc.total_pages}, Chunks: {len(chunks)}, Tokens: {len(token_records)}, Avg Conf: {ocr_doc.average_confidence:.4f}"
    )

    return DocumentIngestResponse(
        document_id=doc_id,
        filename=original_filename,
        pages=ocr_doc.total_pages,
        chunks=len(chunks),
        average_confidence=ocr_doc.average_confidence,
        min_confidence=ocr_doc.min_confidence,
        status="success",
        message="Document successfully processed, chunked, and indexed with OCR confidence in MongoDB Atlas.",
    )
