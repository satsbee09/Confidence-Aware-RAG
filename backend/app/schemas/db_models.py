from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.evidence import EvidenceWord


class OCRTokenRecord(BaseModel):
    """
    Word-level OCR token record stored in MongoDB ocr_tokens collection.
    """
    token_id: str = Field(..., description="Unique token ID, e.g. doc123_p1_t45")
    document_id: str = Field(..., description="Parent document UUID")
    page_number: int = Field(..., ge=1, description="1-indexed page number")
    token_index: int = Field(..., ge=0, description="0-indexed order on page")
    text: str = Field(..., description="Recognized token text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Optical confidence score")
    bbox: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0], description="Bounding box [x0, y0, x1, y1]")
    line_number: Optional[int] = Field(default=None)


class QueryHistoryRecord(BaseModel):
    """
    Persisted query record stored in MongoDB queries collection.
    """
    query_id: str = Field(..., description="Unique query execution UUID")
    query: str = Field(..., description="User query text")
    answer: str = Field(..., description="Generated grounded response")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Answer confidence score")
    risk_level: str = Field(..., description="LOW_RISK, MEDIUM_RISK, or HIGH_RISK")
    overall_warning: Optional[str] = Field(default=None)
    model: str = Field(default="groq/compound-mini")
    document_id: Optional[str] = Field(default=None)
    retrieved_chunks: List[str] = Field(default_factory=list)
    source_count: int = Field(default=0)
    mode: str = Field(default="confidence_aware")
    execution_time_ms: float = Field(default=0.0)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EvidenceHistoryRecord(BaseModel):
    """
    Persisted evidence item stored in MongoDB evidence collection.
    """
    evidence_id: str = Field(..., description="Unique evidence UUID")
    query_id: str = Field(..., description="Associated query execution UUID")
    document_id: Optional[str] = Field(default=None)
    document_name: Optional[str] = Field(default=None)
    chunk_id: Optional[str] = Field(default=None)
    page_number: int = Field(..., ge=1)
    evidence_text: str = Field(default="")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    min_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    risk: str = Field(default="LOW")
    flagged: bool = Field(default=False)
    tokens: List[EvidenceWord] = Field(default_factory=list)
    token_ids: List[str] = Field(default_factory=list)
    page_width: float = Field(default=595.0)
    page_height: float = Field(default=842.0)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
