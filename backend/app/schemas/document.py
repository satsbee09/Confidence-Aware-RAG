from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentSummary(BaseModel):
    """
    Summary representation of an ingested document for dashboard and list endpoints.
    """
    document_id: str = Field(..., description="Unique document UUID")
    filename: str = Field(..., description="Original filename of the document")
    pages: int = Field(..., ge=1, description="Total number of processed pages")
    chunks: int = Field(..., ge=0, description="Total number of generated chunks")
    average_confidence: float = Field(..., ge=0.0, le=1.0, description="Mean OCR confidence of document")
    min_confidence: float = Field(..., ge=0.0, le=1.0, description="Lowest single word confidence")
    file_size_bytes: int = Field(default=0, description="Original file size in bytes")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC creation timestamp"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary additional metadata")


class DocumentIngestResponse(BaseModel):
    """
    Response returned upon successful PDF or image ingestion.
    """
    document_id: str = Field(..., description="Unique document UUID")
    filename: str = Field(..., description="Uploaded filename")
    pages: int = Field(..., ge=1, description="Number of pages ingested")
    chunks: int = Field(..., ge=0, description="Number of chunks created and indexed")
    average_confidence: float = Field(..., ge=0.0, le=1.0, description="Mean OCR confidence across document")
    min_confidence: float = Field(..., ge=0.0, le=1.0, description="Lowest OCR token confidence in document")
    status: str = Field(default="success", description="Ingestion status")
    message: str = Field(default="Document successfully ingested and indexed into vector store")


class DocumentDeleteResponse(BaseModel):
    """
    Response returned when a document is deleted.
    """
    document_id: str = Field(..., description="Deleted document UUID")
    status: str = Field(default="success")
    message: str = Field(description="Deletion status message")
