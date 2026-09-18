from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class OCRWord(BaseModel):
    """
    Word-level OCR token representation with confidence score and bounding box.
    """
    text: str = Field(..., description="Recognized word text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Normalized OCR confidence score (0.0 - 1.0)")
    page: int = Field(..., ge=1, description="1-indexed document page number")
    bbox: List[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.0, 0.0],
        description="Bounding box [x_min, y_min, x_max, y_max]"
    )
    line_number: Optional[int] = Field(default=None, description="Line number on the page")

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v: Any) -> float:
        try:
            val = float(v)
            # If engine outputs 0-100 scale, normalize to 0.0-1.0
            if val > 1.0:
                val = val / 100.0
            return max(0.0, min(1.0, round(val, 4)))
        except (ValueError, TypeError):
            return 0.0


class OCRLine(BaseModel):
    """
    Line-level OCR aggregation preserving constituent words and line bounding box.
    """
    text: str = Field(..., description="Full text content of the recognized line")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Mean OCR confidence of the line")
    page: int = Field(..., ge=1, description="1-indexed page number")
    bbox: List[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.0, 0.0],
        description="Line bounding box [x_min, y_min, x_max, y_max]"
    )
    line_number: int = Field(..., ge=1, description="1-indexed line index on the page")
    words: List[OCRWord] = Field(default_factory=list, description="Constituent words in the line")


class OCRPage(BaseModel):
    """
    Page-level OCR result containing lines, words, dimensions, and page statistics.
    """
    page: int = Field(..., ge=1, description="1-indexed page number")
    width: int = Field(default=0, description="Page width in pixels")
    height: int = Field(default=0, description="Page height in pixels")
    lines: List[OCRLine] = Field(default_factory=list, description="Recognized lines on this page")
    words: List[OCRWord] = Field(default_factory=list, description="All words on this page in reading order")
    text: str = Field(default="", description="Aggregated full page text")
    average_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Weighted/mean confidence of the page")
    min_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Lowest single word confidence on page")
    error: Optional[str] = Field(default=None, description="Error message if page processing failed partially")


class OCRDocument(BaseModel):
    """
    Complete document-level OCR result preserving hierarchical confidence and metadata.
    """
    doc_id: str = Field(..., description="Unique document UUID")
    filename: str = Field(..., description="Original filename of the ingested document")
    total_pages: int = Field(..., ge=1, description="Total number of pages processed")
    pages: List[OCRPage] = Field(default_factory=list, description="List of processed pages")
    all_words: List[OCRWord] = Field(default_factory=list, description="Flattened list of all words across all pages")
    full_text: str = Field(default="", description="Complete document text concatenated across pages")
    average_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Document-wide average OCR confidence")
    min_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Lowest word confidence across document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional document metadata (engine, timestamps)")
