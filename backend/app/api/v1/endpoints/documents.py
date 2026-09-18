from pathlib import Path
from typing import List, Optional, Dict, Any
import io
import fitz  # PyMuPDF
from PIL import Image
from fastapi import APIRouter, HTTPException, status, Response, UploadFile, File
from loguru import logger

from app.core.config import settings
from app.schemas.document import DocumentSummary, DocumentDeleteResponse, DocumentIngestResponse
from app.schemas.page import PageSummary
from app.repositories import (
    get_document_repository,
    get_page_repository,
    get_ocr_token_repository,
    get_chunk_repository,
    get_vector_store,
)
from app.api.v1.endpoints.ingest import ingest_document

router = APIRouter()

# Page Image Cache: (doc_id, page_num, dpi_scale) -> png_bytes, width, height
_PAGE_IMAGE_CACHE: Dict[str, bytes] = {}


@router.post(
    "/documents/upload",
    response_model=DocumentIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and Ingest Scanned Document (Alias to /ingest)",
    description="Upload a scanned PDF or image document and process through the complete Confidence-Aware pipeline.",
)
async def upload_document(file: UploadFile = File(...)) -> DocumentIngestResponse:
    """Unified document upload and ingestion endpoint."""
    return await ingest_document(file=file)


@router.get(
    "/documents",
    response_model=List[DocumentSummary],
    status_code=status.HTTP_200_OK,
    summary="List Ingested Documents",
    description="Returns metadata, page counts, chunk totals, and average OCR confidences for all ingested documents.",
)
async def list_documents() -> List[DocumentSummary]:
    """Retrieve list of all ingested documents."""
    doc_repo = get_document_repository()
    return doc_repo.list_documents()


@router.get(
    "/documents/{document_id}",
    response_model=DocumentSummary,
    status_code=status.HTTP_200_OK,
    summary="Get Document Summary",
    description="Retrieve details and OCR confidence statistics for a specific document.",
)
async def get_document(document_id: str) -> DocumentSummary:
    """Retrieve metadata for a single document."""
    doc_repo = get_document_repository()
    doc = doc_repo.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )
    return doc


@router.get(
    "/documents/{document_id}/pages",
    response_model=List[PageSummary],
    status_code=status.HTTP_200_OK,
    summary="Get Document Pages",
    description="Retrieve all processed pages, dimensions, and token statistics for a given document.",
)
async def get_document_pages(document_id: str) -> List[PageSummary]:
    """Retrieve list of pages for a specific document."""
    doc_repo = get_document_repository()
    doc = doc_repo.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )

    page_repo = get_page_repository()
    pages = page_repo.list_pages_by_document(document_id)
    if not pages:
        # Generate virtual page records from document summary if needed
        for p in range(1, doc.pages + 1):
            pages.append(
                PageSummary(
                    page_id=f"{document_id}_page_{p}",
                    document_id=document_id,
                    page_number=p,
                    ocr_confidence=doc.average_confidence,
                    width=595.0,
                    height=842.0,
                )
            )
    return pages


@router.get(
    "/documents/{document_id}/pages/{page_number}",
    response_model=PageSummary,
    status_code=status.HTTP_200_OK,
    summary="Get Page Details",
    description="Retrieve page dimensions and OCR confidence statistics for a specific page number.",
)
async def get_page_detail(document_id: str, page_number: int) -> PageSummary:
    """Retrieve metadata for a specific document page."""
    page_repo = get_page_repository()
    page = page_repo.get_page(document_id, page_number)
    if not page:
        doc_repo = get_document_repository()
        doc = doc_repo.get_document(document_id)
        if not doc or page_number > doc.pages or page_number < 1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page {page_number} for document '{document_id}' not found.",
            )
        return PageSummary(
            page_id=f"{document_id}_page_{page_number}",
            document_id=document_id,
            page_number=page_number,
            ocr_confidence=doc.average_confidence,
            width=595.0,
            height=842.0,
        )
    return page


@router.get(
    "/documents/{document_id}/pages/{page_number}/image",
    status_code=status.HTTP_200_OK,
    summary="Get Rendered Document Page Image",
    description="Renders the requested PDF page to a high-resolution PNG image for live evidence visualization.",
)
async def get_page_image(
    document_id: str,
    page_number: int,
    scale: float = 2.0,
) -> Response:
    """
    Renders and returns a page image (PNG) for a given document and 1-indexed page number.
    Caches rendered images for high-speed UI interaction.
    """
    if page_number < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be 1 or greater.",
        )

    cache_key = f"{document_id}_{page_number}_{scale}"
    if cache_key in _PAGE_IMAGE_CACHE:
        return Response(
            content=_PAGE_IMAGE_CACHE[cache_key],
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    doc_repo = get_document_repository()
    doc_summary = doc_repo.get_document(document_id)
    if not doc_summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    saved_file_str = doc_summary.metadata.get("saved_file")
    if not saved_file_str or not Path(saved_file_str).exists():
        # Check if original file is in upload dir
        candidates = list(settings.UPLOAD_DIR.glob(f"{document_id}_*"))
        if candidates and candidates[0].exists():
            file_path = candidates[0]
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Original document file for '{document_id}' not found on server disk.",
            )
    else:
        file_path = Path(saved_file_str)

    try:
        if file_path.suffix.lower() == ".pdf":
            pdf_doc = fitz.open(str(file_path))
            total_pages = len(pdf_doc)
            if page_number > total_pages:
                pdf_doc.close()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Page {page_number} exceeds document page count of {total_pages}.",
                )

            page = pdf_doc.load_page(page_number - 1)
            rect = page.rect
            orig_w, orig_h = rect.width, rect.height

            # High-res rasterization (e.g. scale 2.0 = ~150-200 DPI)
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            png_bytes = pix.tobytes("png")
            pdf_doc.close()

            _PAGE_IMAGE_CACHE[cache_key] = png_bytes
            return Response(
                content=png_bytes,
                media_type="image/png",
                headers={
                    "Cache-Control": "public, max-age=3600",
                    "X-Page-Width": str(round(orig_w, 2)),
                    "X-Page-Height": str(round(orig_h, 2)),
                    "X-Total-Pages": str(total_pages),
                },
            )
        else:
            # Standalone image file
            with open(file_path, "rb") as img_f:
                img = Image.open(img_f).convert("RGB")
                orig_w, orig_h = img.size
                out_buf = io.BytesIO()
                img.save(out_buf, format="PNG")
                png_bytes = out_buf.getvalue()

            _PAGE_IMAGE_CACHE[cache_key] = png_bytes
            return Response(
                content=png_bytes,
                media_type="image/png",
                headers={
                    "Cache-Control": "public, max-age=3600",
                    "X-Page-Width": str(orig_w),
                    "X-Page-Height": str(orig_h),
                    "X-Total-Pages": "1",
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering page image for doc '{document_id}' page {page_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to render document page: {str(e)}",
        )


@router.delete(
    "/documents/{document_id}",
    response_model=DocumentDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Document",
    description="Deletes document from MongoDB collections, removes vectors from index, and cleans up storage.",
)
async def delete_document(document_id: str) -> DocumentDeleteResponse:
    """Delete document, pages, tokens, chunks, and its indexed vectors."""
    doc_repo = get_document_repository()
    doc = doc_repo.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )

    # 1. Delete from Vector Store
    vector_store = get_vector_store()
    vector_store.delete_document(document_id)

    # 2. Delete source file if exists
    if "saved_file" in doc.metadata:
        file_path = Path(doc.metadata["saved_file"])
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Removed source file: {file_path}")
            except Exception as e:
                logger.warning(f"Could not delete source file {file_path}: {e}")

    # 3. Clean page image cache
    for k in list(_PAGE_IMAGE_CACHE.keys()):
        if k.startswith(f"{document_id}_"):
            _PAGE_IMAGE_CACHE.pop(k, None)

    # 4. Cascade delete in MongoDB
    page_repo = get_page_repository()
    page_repo.delete_pages_by_document(document_id)

    token_repo = get_ocr_token_repository()
    token_repo.delete_tokens_by_document(document_id)

    chunk_repo = get_chunk_repository()
    chunk_repo.delete_chunks_by_document(document_id)

    # 5. Delete document record
    doc_repo.delete_document(document_id)

    logger.info(f"Document '{document_id}' deleted completely from MongoDB and vector index.")
    return DocumentDeleteResponse(
        document_id=document_id,
        status="success",
        message=f"Document '{doc.filename}' and all associated pages, tokens, chunks, and vectors were deleted successfully.",
    )
