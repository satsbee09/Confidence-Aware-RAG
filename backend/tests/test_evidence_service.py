import pytest
from app.schemas.chunk import Chunk
from app.schemas.ocr import OCRWord
from app.schemas.retrieval import ScoredChunk
from app.services.embedding_service import SentenceTransformerEmbeddingService
from app.services.evidence_service import EvidenceQualityService


@pytest.fixture(scope="module")
def embedding_service():
    return SentenceTransformerEmbeddingService()


def test_evidence_analysis_flags_noisy_key_sentence(embedding_service):
    """
    Test that evidence analyzer identifies the relevant sentence answering the query
    and flags low-confidence tokens (e.g., date and amount).
    """
    evidence_svc = EvidenceQualityService(
        embedding_service=embedding_service,
        evidence_threshold=0.60,
    )

    # Sentence 1: Administrative preamble (high confidence)
    words_s1 = [
        OCRWord(text="This", confidence=0.98, page=4),
        OCRWord(text="is", confidence=0.99, page=4),
        OCRWord(text="an", confidence=0.95, page=4),
        OCRWord(text="official", confidence=0.97, page=4),
        OCRWord(text="gazette", confidence=0.96, page=4),
        OCRWord(text="notification.", confidence=0.94, page=4),
    ]

    # Sentence 2: Key fact directly answering "When was the application rejected?"
    # Note: "2025" and "rejected" have low OCR confidence
    words_s2 = [
        OCRWord(text="The", confidence=0.95, page=4),
        OCRWord(text="application", confidence=0.92, page=4),
        OCRWord(text="was", confidence=0.96, page=4),
        OCRWord(text="rejected", confidence=0.52, page=4),  # < 0.60
        OCRWord(text="on", confidence=0.95, page=4),
        OCRWord(text="12", confidence=0.90, page=4),
        OCRWord(text="June", confidence=0.88, page=4),
        OCRWord(text="2025.", confidence=0.41, page=4),  # < 0.60
    ]

    chunk_words = words_s1 + words_s2
    chunk = Chunk(
        chunk_id="chunk_test_ev",
        doc_id="doc_rti_001",
        chunk_text="This is an official gazette notification. The application was rejected on 12 June 2025.",
        confidence_score=0.82,
        raw_confidence=0.87,
        min_confidence=0.41,
        page=4,
        words=chunk_words,
    )

    scored_candidate = ScoredChunk(
        chunk=chunk,
        similarity=0.85,
        ocr_confidence=0.82,
        final_score=0.77,
        rank=1,
    )

    query = "When was the application rejected?"
    report = evidence_svc.analyze_evidence(query, [scored_candidate])

    assert len(report.analyzed_chunks) == 1
    analyzed = report.analyzed_chunks[0]

    # The chunk must be flagged because key sentence s2 contains low-confidence tokens
    assert analyzed.flagged is True
    assert analyzed.min_word_confidence == 0.41
    assert report.overall_risk_level == "HIGH_RISK"
    assert report.flagged_count >= 1
    assert report.warning_message is not None
    assert "low-confidence OCR text" in report.warning_message

    # Check key sentence details
    flagged_sentences = [s for s in analyzed.key_sentences if s.flagged]
    assert len(flagged_sentences) > 0
    target_sentence = flagged_sentences[0]

    low_conf_token_texts = [w.text for w in target_sentence.low_confidence_words]
    assert "2025." in low_conf_token_texts or "rejected" in low_conf_token_texts


def test_evidence_analysis_clean_document(embedding_service):
    """Verify that high-confidence evidence is marked LOW_RISK with no warnings."""
    evidence_svc = EvidenceQualityService(
        embedding_service=embedding_service,
        evidence_threshold=0.60,
    )

    clean_words = [
        OCRWord(text="The", confidence=0.98, page=1),
        OCRWord(text="competent", confidence=0.96, page=1),
        OCRWord(text="authority", confidence=0.97, page=1),
        OCRWord(text="granted", confidence=0.99, page=1),
        OCRWord(text="sanction.", confidence=0.95, page=1),
    ]

    clean_chunk = Chunk(
        chunk_id="chunk_clean_1",
        doc_id="doc_clean",
        chunk_text="The competent authority granted sanction.",
        confidence_score=0.97,
        raw_confidence=0.97,
        min_confidence=0.95,
        page=1,
        words=clean_words,
    )

    candidate = ScoredChunk(
        chunk=clean_chunk,
        similarity=0.90,
        ocr_confidence=0.97,
        final_score=0.88,
        rank=1,
    )

    query = "Did the authority grant sanction?"
    report = evidence_svc.analyze_evidence(query, [candidate])

    assert report.overall_risk_level == "LOW_RISK"
    assert report.flagged_count == 0
    assert report.warning_message is None
    assert report.analyzed_chunks[0].flagged is False
