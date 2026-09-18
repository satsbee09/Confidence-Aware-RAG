import pytest
from app.schemas.ocr import OCRDocument, OCRPage, OCRWord, OCRLine
from app.schemas.chunk import Chunk
from app.services.chunking_service import ConfidenceAwareChunker


def _build_test_document() -> OCRDocument:
    """Helper to build a multi-page synthetic OCRDocument with mixed confidence."""
    # Page 1: High confidence text
    p1_words = [
        OCRWord(text="In", confidence=0.98, page=1),
        OCRWord(text="the", confidence=0.99, page=1),
        OCRWord(text="High", confidence=0.95, page=1),
        OCRWord(text="Court", confidence=0.97, page=1),
        OCRWord(text="of", confidence=0.99, page=1),
        OCRWord(text="Delhi.", confidence=0.96, page=1),
        OCRWord(text="Writ", confidence=0.94, page=1),
        OCRWord(text="Petition", confidence=0.95, page=1),
        OCRWord(text="No.", confidence=0.96, page=1),
        OCRWord(text="1042/2024.", confidence=0.92, page=1),
    ]
    p1_lines = [
        OCRLine(text="In the High Court of Delhi.", confidence=0.97, page=1, line_number=1, words=p1_words[:6]),
        OCRLine(text="Writ Petition No. 1042/2024.", confidence=0.94, page=1, line_number=2, words=p1_words[6:]),
    ]
    page1 = OCRPage(
        page=1,
        lines=p1_lines,
        words=p1_words,
        text="In the High Court of Delhi.\nWrit Petition No. 1042/2024.",
        average_confidence=0.96,
        min_confidence=0.92,
    )

    # Page 2: Noisy text with low-confidence tokens (e.g. date and fine amount)
    p2_words = [
        OCRWord(text="The", confidence=0.95, page=2),
        OCRWord(text="petitioner", confidence=0.92, page=2),
        OCRWord(text="failed", confidence=0.88, page=2),
        OCRWord(text="to", confidence=0.98, page=2),
        OCRWord(text="deposit", confidence=0.90, page=2),
        OCRWord(text="fine", confidence=0.85, page=2),
        OCRWord(text="of", confidence=0.95, page=2),
        OCRWord(text="Rs.", confidence=0.80, page=2),
        OCRWord(text="50000", confidence=0.35, page=2),  # LOW CONFIDENCE (35%)
        OCRWord(text="on", confidence=0.90, page=2),
        OCRWord(text="12/06/2025.", confidence=0.42, page=2),  # LOW CONFIDENCE (42%)
    ]
    p2_lines = [
        OCRLine(
            text="The petitioner failed to deposit fine of Rs. 50000 on 12/06/2025.",
            confidence=0.75,
            page=2,
            line_number=1,
            words=p2_words,
        )
    ]
    page2 = OCRPage(
        page=2,
        lines=p2_lines,
        words=p2_words,
        text="The petitioner failed to deposit fine of Rs. 50000 on 12/06/2025.",
        average_confidence=0.75,
        min_confidence=0.35,
    )

    return OCRDocument(
        doc_id="doc-test-100",
        filename="court_order.pdf",
        total_pages=2,
        pages=[page1, page2],
        all_words=p1_words + p2_words,
        full_text=page1.text + "\n\n" + page2.text,
        average_confidence=0.855,
        min_confidence=0.35,
    )


def test_chunking_preserves_sentences_and_metrics():
    """Test chunking with low min_tokens to verify metric propagation."""
    doc = _build_test_document()
    # Use small min_tokens for testing boundary division
    chunker = ConfidenceAwareChunker(min_tokens=5, max_tokens=15, overlap_tokens=2, low_conf_threshold=0.50)
    chunks = chunker.create_chunks(doc)

    assert len(chunks) >= 2
    for chunk in chunks:
        assert isinstance(chunk, Chunk)
        assert chunk.doc_id == "doc-test-100"
        assert len(chunk.words) > 0
        assert 0.0 <= chunk.confidence_score <= 1.0
        assert 0.0 <= chunk.raw_confidence <= 1.0
        assert 0.0 <= chunk.min_confidence <= 1.0


def test_chunking_applies_low_confidence_penalty():
    """Verify that chunks with noisy words are penalized below raw average."""
    doc = _build_test_document()
    chunker = ConfidenceAwareChunker(min_tokens=5, max_tokens=20, low_conf_threshold=0.50)
    chunks = chunker.create_chunks(doc)

    # Find the chunk containing the noisy words on page 2
    noisy_chunk = next(c for c in chunks if "50000" in c.chunk_text)

    assert len(noisy_chunk.low_confidence_words) >= 2
    assert noisy_chunk.min_confidence == 0.35
    # The penalized confidence must be strictly lower than the raw weighted confidence
    assert noisy_chunk.confidence_score < noisy_chunk.raw_confidence
    assert noisy_chunk.page == 2
