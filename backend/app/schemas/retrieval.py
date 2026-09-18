from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.chunk import Chunk


class ScoredChunk(BaseModel):
    """
    Candidate chunk retrieved from vector database with semantic similarity
    and optical confidence metrics.
    """
    chunk: Chunk = Field(..., description="Retrieved chunk payload and OCR metadata")
    similarity: float = Field(..., ge=-1.0, le=1.0, description="Cosine semantic similarity score (0.0 to 1.0)")
    ocr_confidence: float = Field(..., ge=0.0, le=1.0, description="Effective OCR confidence score of the chunk")
    final_score: float = Field(..., description="Reranked composite score: sim * (w_s + w_c * conf)")
    rank: int = Field(default=1, ge=1, description="Rank position in final retrieved list")


class RetrievalResult(BaseModel):
    """
    Complete retrieval response containing top candidates before and after reranking.
    """
    query: str = Field(..., description="User search query")
    doc_id: Optional[str] = Field(default=None, description="Queried document ID, if scoped")
    candidates_retrieved: int = Field(..., description="Number of candidates retrieved from vector store")
    top_candidates: List[ScoredChunk] = Field(default_factory=list, description="Top reranked candidates")
    execution_time_ms: float = Field(default=0.0, description="Retrieval and reranking latency in milliseconds")
