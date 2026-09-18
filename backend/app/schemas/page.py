from typing import Optional
from pydantic import BaseModel, Field


class PageSummary(BaseModel):
    """
    Representation of a processed document page stored in MongoDB pages collection.
    """
    page_id: str = Field(..., description="Unique page identifier, e.g., doc123_page_1")
    document_id: str = Field(..., description="Parent document UUID")
    page_number: int = Field(..., ge=1, description="1-indexed page number")
    image_path: Optional[str] = Field(default=None, description="Path to rendered page image")
    width: float = Field(default=595.0, description="Page width in PDF/pixel units")
    height: float = Field(default=842.0, description="Page height in PDF/pixel units")
    ocr_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Page OCR confidence score")
    token_count: int = Field(default=0, ge=0, description="Total recognized words on this page")
    text_preview: Optional[str] = Field(default="", description="Text preview snippet of page")
