import pytest
import numpy as np
from pathlib import Path
from app.schemas.chunk import Chunk
from app.schemas.ocr import OCRWord
from app.services.embedding_service import SentenceTransformerEmbeddingService
from app.repositories.vector_store import NumpyVectorStore


@pytest.fixture(scope="module")
def embedding_service():
    """Module-level fixture to load embedding model once for tests."""
    return SentenceTransformerEmbeddingService()


def test_embedding_service_properties(embedding_service):
    """Verify embedding service dimension and normalization."""
    assert embedding_service.dimension == 384

    text = "The High Court of Delhi granted the writ petition."
    vec = embedding_service.encode_text(text)

    assert isinstance(vec, np.ndarray)
    assert vec.shape == (384,)
    assert vec.dtype == np.float32

    # Verify L2 normalization: norm should be approximately 1.0
    norm = np.linalg.norm(vec)
    assert pytest.approx(norm, 1e-4) == 1.0


def test_embedding_service_batch_encoding(embedding_service):
    """Verify batch encoding shape and consistency."""
    texts = [
        "Right to Information Act section 6(1).",
        "Gazette notification regarding land survey.",
        "Order issued by the Revenue Department.",
    ]
    batch_vecs = embedding_service.encode_batch(texts)

    assert batch_vecs.shape == (3, 384)
    for i in range(3):
        assert pytest.approx(np.linalg.norm(batch_vecs[i]), 1e-4) == 1.0


def test_vector_store_crud_and_search(tmp_path: Path, embedding_service):
    """Verify vector store indexing, similarity search, filtering, and deletion."""
    storage_dir = tmp_path / "test_storage"
    vstore = NumpyVectorStore(dimension=384, storage_dir=storage_dir)

    # Create test chunks across two distinct documents
    chunk1_doc1 = Chunk(
        chunk_id="c1",
        doc_id="doc_rti",
        chunk_text="The RTI application was rejected due to lack of valuation certificate.",
        confidence_score=0.88,
        raw_confidence=0.92,
        min_confidence=0.70,
        page=1,
    )
    chunk2_doc1 = Chunk(
        chunk_id="c2",
        doc_id="doc_rti",
        chunk_text="Applicant Ramesh Kumar requested copies of revenue inspection reports.",
        confidence_score=0.95,
        raw_confidence=0.96,
        min_confidence=0.90,
        page=2,
    )
    chunk3_doc2 = Chunk(
        chunk_id="c3",
        doc_id="doc_court",
        chunk_text="The High Court sentenced the accused under Section 420 of IPC.",
        confidence_score=0.91,
        raw_confidence=0.93,
        min_confidence=0.85,
        page=1,
    )

    chunks_doc1 = [chunk1_doc1, chunk2_doc1]
    vecs_doc1 = embedding_service.encode_batch([c.chunk_text for c in chunks_doc1])
    vstore.add_chunks(chunks_doc1, vecs_doc1)

    vstore.add_chunks([chunk3_doc2], embedding_service.encode_batch([chunk3_doc2.chunk_text]))

    assert vstore.count() == 3
    assert set(vstore.list_documents()) == {"doc_rti", "doc_court"}

    # Search for rejection reason without document filter
    query_vec = embedding_service.encode_text("Why was the RTI application denied?")
    results = vstore.search(query_vec, top_k=2)

    assert len(results) == 2
    top_chunk, sim = results[0]
    assert top_chunk.chunk_id == "c1"
    assert sim > 0.40

    # Search with document filter
    scoped_results = vstore.search(query_vec, top_k=2, doc_id="doc_court")
    assert len(scoped_results) == 1
    assert scoped_results[0][0].doc_id == "doc_court"

    # Test persistence & reload
    vstore.save_to_disk()
    reloaded_store = NumpyVectorStore(dimension=384, storage_dir=storage_dir)
    assert reloaded_store.count() == 3
    reloaded_results = reloaded_store.search(query_vec, top_k=1)
    assert reloaded_results[0][0].chunk_id == "c1"

    # Test document deletion
    deleted = reloaded_store.delete_document("doc_court")
    assert deleted is True
    assert reloaded_store.count() == 2
    assert reloaded_store.list_documents() == ["doc_rti"]
