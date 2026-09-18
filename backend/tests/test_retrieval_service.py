import pytest
import numpy as np
from pathlib import Path
from app.schemas.chunk import Chunk
from app.schemas.ocr import OCRWord
from app.services.embedding_service import SentenceTransformerEmbeddingService
from app.repositories.vector_store import NumpyVectorStore
from app.services.retrieval_service import RetrievalService


@pytest.fixture(scope="module")
def embedding_service():
    return SentenceTransformerEmbeddingService()


def test_calculate_rerank_score_formula():
    """Verify reranking formula: final_score = sim * (w_s + w_c * conf)."""
    retrieval = RetrievalService(similarity_weight=0.5, confidence_weight=0.5)

    # Test clean chunk: sim 0.90, conf 1.0 -> 0.90 * (0.5 + 0.5) = 0.90
    score_clean = retrieval.calculate_rerank_score(similarity=0.90, ocr_confidence=1.0)
    assert score_clean == 0.90

    # Test noisy chunk: sim 0.90, conf 0.40 -> 0.90 * (0.5 + 0.2) = 0.63
    score_noisy = retrieval.calculate_rerank_score(similarity=0.90, ocr_confidence=0.40)
    assert score_noisy == 0.63

    # Zero similarity gives zero
    assert retrieval.calculate_rerank_score(similarity=0.0, ocr_confidence=0.9) == 0.0


def test_confidence_reranking_inversion(tmp_path: Path, embedding_service):
    """
    Key Research Experiment Test:
    Demonstrate that a clean, highly reliable chunk outranks a noisy chunk
    with artificially high semantic similarity.
    """
    storage_dir = tmp_path / "retrieval_test_storage"
    vstore = NumpyVectorStore(dimension=384, storage_dir=storage_dir)
    retrieval_svc = RetrievalService(
        embedding_service=embedding_service,
        vector_store=vstore,
        similarity_weight=0.5,
        confidence_weight=0.5,
    )

    # Chunk A: Noisy, corrupted OCR text with high keyword overlap
    chunk_a = Chunk(
        chunk_id="chunk_noisy",
        doc_id="doc_001",
        chunk_text="The RTI application was rejected for non-submission on 12/06/2025.",
        confidence_score=0.35,  # Low OCR confidence (garbled text)
        raw_confidence=0.45,
        min_confidence=0.30,
        page=1,
    )

    # Chunk B: High-confidence clean OCR text explaining the same decision
    chunk_b = Chunk(
        chunk_id="chunk_clean",
        doc_id="doc_001",
        chunk_text="Order details: Application refused by competent authority due to missing Form 4-A.",
        confidence_score=0.98,  # High OCR confidence (clear scan)
        raw_confidence=0.98,
        min_confidence=0.95,
        page=2,
    )

    chunks = [chunk_a, chunk_b]
    vecs = embedding_service.encode_batch([c.chunk_text for c in chunks])
    vstore.add_chunks(chunks, vecs)

    query = "Why was the application rejected?"

    # 1. Baseline Retrieval (No confidence reranking)
    baseline_result = retrieval_svc.retrieve(
        query=query,
        use_confidence_reranking=False,
        top_k=2,
    )
    assert len(baseline_result.top_candidates) == 2
    # In baseline, the chunk with highest semantic similarity ranks first
    assert baseline_result.top_candidates[0].rank == 1

    # 2. Proposed Confidence-Aware Retrieval (With confidence reranking)
    conf_aware_result = retrieval_svc.retrieve(
        query=query,
        use_confidence_reranking=True,
        top_k=2,
    )
    assert len(conf_aware_result.top_candidates) == 2

    # The clean chunk must receive higher composite score than the corrupted chunk
    clean_candidate = next(
        c for c in conf_aware_result.top_candidates if c.chunk.chunk_id == "chunk_clean"
    )
    noisy_candidate = next(
        c for c in conf_aware_result.top_candidates if c.chunk.chunk_id == "chunk_noisy"
    )

    assert clean_candidate.final_score > noisy_candidate.final_score
    assert conf_aware_result.top_candidates[0].chunk.chunk_id == "chunk_clean"
    assert conf_aware_result.top_candidates[0].rank == 1
