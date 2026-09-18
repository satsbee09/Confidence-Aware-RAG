from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class EvidenceWord(BaseModel):
    """
    Word token inside an evidence sentence with optical confidence and risk tag.
    """
    text: str = Field(..., description="Word text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Normalized OCR confidence")
    page: int = Field(default=1, description="Page number where word appears")
    bbox: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    is_low_confidence: bool = Field(default=False, description="Whether word is below threshold")


class EvidenceSentence(BaseModel):
    """
    Sentence unit extracted from a retrieved chunk with query relevance and token confidence.
    """
    sentence_text: str = Field(..., description="Text of the evidence sentence")
    sentence_confidence: float = Field(..., ge=0.0, le=1.0, description="Mean OCR confidence of sentence words")
    similarity_to_query: float = Field(default=0.0, description="Semantic similarity score to user query")
    flagged: bool = Field(default=False, description="True if sentence contains words below evidence threshold")
    low_confidence_words: List[EvidenceWord] = Field(
        default_factory=list,
        description="Words inside this sentence that require verification"
    )
    all_words: List[EvidenceWord] = Field(
        default_factory=list,
        description="All words in this sentence with confidence and bounding boxes"
    )


class AnalyzedEvidenceChunk(BaseModel):
    """
    Retrieved chunk evaluated by Evidence Quality Analysis.
    """
    chunk_id: str = Field(..., description="Chunk UUID")
    doc_id: str = Field(..., description="Parent document UUID")
    page: int = Field(..., description="Primary page number")
    page_range: List[int] = Field(default_factory=list, description="All pages spanned by chunk")
    page_width: float = Field(default=595.0, description="Original page width in PDF/pixel units")
    page_height: float = Field(default=842.0, description="Original page height in PDF/pixel units")
    chunk_text: str = Field(..., description="Full text of the chunk")
    chunk_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall chunk confidence score")
    similarity: float = Field(default=0.0, description="Semantic cosine similarity to user query")
    final_score: float = Field(default=0.0, description="Blended rerank score (0.5 Sim + 0.5 OCR)")
    key_sentences: List[EvidenceSentence] = Field(
        default_factory=list,
        description="Top query-relevant sentences inside the chunk"
    )
    flagged: bool = Field(default=False, description="True if any key sentence has low-confidence tokens")
    min_word_confidence: float = Field(default=1.0, description="Lowest word confidence in key sentences")


class EvidenceQualityReport(BaseModel):
    """
    Comprehensive Evidence Quality Report passed to LLM and Frontend.
    """
    query: str = Field(..., description="User query evaluated")
    analyzed_chunks: List[AnalyzedEvidenceChunk] = Field(
        default_factory=list,
        description="Top analyzed evidence chunks (typically top 3)"
    )
    overall_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Mean evidence confidence across all key supporting sentences"
    )
    overall_risk_level: Literal["LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"] = Field(
        default="LOW_RISK",
        description="Risk level classification based on evidence confidence and low-confidence flags"
    )
    flagged_count: int = Field(default=0, description="Total number of flagged evidence sentences")
    warning_message: Optional[str] = Field(
        default=None,
        description="User-facing warning advising verification against original document"
    )
