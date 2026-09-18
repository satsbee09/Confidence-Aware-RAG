from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.ocr import OCRWord


class Chunk(BaseModel):
    """
    Representation of a confidence-aware text chunk.
    Preserves token-level OCR metrics, natural sentence boundaries, and page provenance.
    """
    chunk_id: str = Field(..., description="Unique chunk UUID")
    doc_id: str = Field(..., description="Parent document UUID")
    chunk_text: str = Field(..., description="Plain text content of the chunk")
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Effective confidence score (weighted average with low-confidence penalty applied)"
    )
    raw_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Raw token-length-weighted average OCR confidence"
    )
    min_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Minimum individual word confidence within this chunk"
    )
    page: int = Field(..., ge=1, description="Primary document page number where this chunk originates")
    page_range: List[int] = Field(
        default_factory=list,
        description="List of all pages spanned by this chunk (for multi-page chunks)"
    )
    page_width: float = Field(default=595.0, description="Original page width in PDF/pixel units")
    page_height: float = Field(default=842.0, description="Original page height in PDF/pixel units")
    token_count: int = Field(default=0, description="Approximate token count of the chunk")
    words: List[OCRWord] = Field(
        default_factory=list,
        description="Constituent OCR words with bounding boxes and individual confidences"
    )
    low_confidence_words: List[OCRWord] = Field(
        default_factory=list,
        description="Words identified below the low confidence threshold"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary additional metadata (source filename, chunk index, etc.)"
    )
