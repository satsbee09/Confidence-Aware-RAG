import mongomock
import pytest
from fastapi.testclient import TestClient

from app.main import create_application
from app.database import (
    mongodb_manager,
    create_indexes,
    DOCUMENTS_COLLECTION,
    PAGES_COLLECTION,
    OCR_TOKENS_COLLECTION,
    CHUNKS_COLLECTION,
    QUERIES_COLLECTION,
    EVIDENCE_COLLECTION,
    EVALUATIONS_COLLECTION,
)
from app.schemas.document import DocumentSummary
from app.schemas.page import PageSummary
from app.schemas.db_models import OCRTokenRecord, QueryHistoryRecord, EvidenceHistoryRecord
from app.schemas.chunk import Chunk
from app.schemas.ocr import OCRWord
from app.schemas.evidence import EvidenceWord
from app.repositories import (
    get_document_repository,
    get_page_repository,
    get_ocr_token_repository,
    get_chunk_repository,
    get_query_repository,
    get_evidence_repository,
    get_evaluation_repository,
    get_vector_store,
)


@pytest.fixture(autouse=True)
def setup_mock_mongodb():
    """Inject an in-memory mongomock database for isolated test execution."""
    client = mongomock.MongoClient()
    mock_db = client["test_confidence_rag"]
    mongodb_manager.set_mock_database(mock_db)
    create_indexes(mock_db)
    yield mock_db
    mock_db.client.drop_database("test_confidence_rag")


def test_mongodb_manager_connection_and_mock(setup_mock_mongodb):
    """Test MongoDB manager retrieves mock database and validates state."""
    db = mongodb_manager.get_database()
    assert db is not None
    assert mongodb_manager.is_connected is True
    assert db.name == "test_confidence_rag"


def test_document_repository_mongodb(setup_mock_mongodb):
    """Test DocumentRepository persists and retrieves documents in MongoDB."""
    repo = get_document_repository()
    doc_summary = DocumentSummary(
        document_id="doc_test_101",
        filename="High_Court_Judgment.pdf",
        pages=5,
        chunks=12,
        average_confidence=0.885,
        min_confidence=0.62,
        file_size_bytes=1048576,
        metadata={"saved_file": "/tmp/doc101.pdf", "status": "processed"},
    )
    repo.save_document(doc_summary)

    # Query back
    fetched = repo.get_document("doc_test_101")
    assert fetched is not None
    assert fetched.filename == "High_Court_Judgment.pdf"
    assert fetched.pages == 5
    assert fetched.average_confidence == 0.885

    # Check MongoDB collection
    mongo_doc = setup_mock_mongodb[DOCUMENTS_COLLECTION].find_one({"_id": "doc_test_101"})
    assert mongo_doc is not None
    assert mongo_doc["filename"] == "High_Court_Judgment.pdf"

    # List documents
    docs = repo.list_documents()
    assert len(docs) >= 1
    assert any(d.document_id == "doc_test_101" for d in docs)

    # Delete
    deleted = repo.delete_document("doc_test_101")
    assert deleted is True
    assert repo.get_document("doc_test_101") is None
    assert setup_mock_mongodb[DOCUMENTS_COLLECTION].find_one({"_id": "doc_test_101"}) is None


def test_page_repository_mongodb(setup_mock_mongodb):
    """Test PageRepository persists page dimensions and confidence in MongoDB."""
    repo = get_page_repository()
    pages = [
        PageSummary(
            page_id="doc_p_1_page_1",
            document_id="doc_p_1",
            page_number=1,
            image_path="storage/pages/doc_p_1/page_1.png",
            width=595.0,
            height=842.0,
            ocr_confidence=0.92,
            token_count=150,
        ),
        PageSummary(
            page_id="doc_p_1_page_2",
            document_id="doc_p_1",
            page_number=2,
            image_path="storage/pages/doc_p_1/page_2.png",
            width=595.0,
            height=842.0,
            ocr_confidence=0.84,
            token_count=210,
        ),
    ]
    repo.save_pages(pages)

    # Query single page
    p1 = repo.get_page("doc_p_1", 1)
    assert p1 is not None
    assert p1.width == 595.0
    assert p1.ocr_confidence == 0.92

    # Query list
    all_pages = repo.list_pages_by_document("doc_p_1")
    assert len(all_pages) == 2
    assert all_pages[0].page_number == 1
    assert all_pages[1].page_number == 2

    # Delete
    deleted_count = repo.delete_pages_by_document("doc_p_1")
    assert deleted_count == 2
    assert repo.get_page("doc_p_1", 1) is None


def test_ocr_token_repository_bbox_preservation(setup_mock_mongodb):
    """Test OCRTokenRepository preserves exact bounding boxes and word confidence without data loss."""
    repo = get_ocr_token_repository()
    tokens = [
        OCRTokenRecord(
            token_id="doc_tok_1_p1_t0",
            document_id="doc_tok_1",
            page_number=1,
            token_index=0,
            text="Penalty",
            confidence=0.95,
            bbox=[100.5, 200.0, 150.0, 220.0],
            line_number=1,
        ),
        OCRTokenRecord(
            token_id="doc_tok_1_p1_t1",
            document_id="doc_tok_1",
            page_number=1,
            token_index=1,
            text="₹50,000",
            confidence=0.48,  # Low confidence token
            bbox=[155.0, 200.0, 210.0, 220.0],
            line_number=1,
        ),
    ]
    repo.bulk_save_tokens(tokens)

    # Retrieve by page
    page_tokens = repo.get_tokens_by_page("doc_tok_1", 1)
    assert len(page_tokens) == 2
    assert page_tokens[0].text == "Penalty"
    assert page_tokens[0].bbox == [100.5, 200.0, 150.0, 220.0]
    assert page_tokens[1].text == "₹50,000"
    assert page_tokens[1].confidence == 0.48
    assert page_tokens[1].bbox == [155.0, 200.0, 210.0, 220.0]

    # Verify MongoDB direct record
    m_tok = setup_mock_mongodb[OCR_TOKENS_COLLECTION].find_one({"_id": "doc_tok_1_p1_t1"})
    assert m_tok is not None
    assert m_tok["text"] == "₹50,000"
    assert m_tok["confidence"] == 0.48

    # Delete
    deleted_cnt = repo.delete_tokens_by_document("doc_tok_1")
    assert deleted_cnt == 2
    assert len(repo.get_tokens_by_page("doc_tok_1", 1)) == 0


def test_chunk_repository_mongodb(setup_mock_mongodb):
    """Test ChunkRepository persists chunks with token links and confidence scores."""
    repo = get_chunk_repository()
    chunk = Chunk(
        chunk_id="chk_001_test",
        doc_id="doc_chk_1",
        chunk_text="The court imposed a fine of ₹50,000 on the respondent.",
        confidence_score=0.86,
        raw_confidence=0.89,
        min_confidence=0.48,
        page=1,
        page_range=[1],
        token_count=10,
        words=[
            OCRWord(text="The", confidence=0.98, page=1, bbox=[10, 10, 25, 20]),
            OCRWord(text="court", confidence=0.97, page=1, bbox=[30, 10, 55, 20]),
            OCRWord(text="imposed", confidence=0.96, page=1, bbox=[60, 10, 95, 20]),
        ],
    )
    repo.save_chunks([chunk])

    # Fetch chunk
    c = repo.get_chunk("chk_001_test")
    assert c is not None
    assert c.doc_id == "doc_chk_1"
    assert c.confidence_score == 0.86
    assert len(c.words) == 3
    assert c.words[1].text == "court"

    # List chunks for doc
    doc_chunks = repo.get_chunks_by_document("doc_chk_1")
    assert len(doc_chunks) == 1

    # Delete
    deleted = repo.delete_chunks_by_document("doc_chk_1")
    assert deleted == 1
    assert repo.get_chunk("chk_001_test") is None


def test_query_and_evidence_repositories(setup_mock_mongodb):
    """Test QueryRepository and EvidenceRepository persistence for Evidence Viewer."""
    q_repo = get_query_repository()
    ev_repo = get_evidence_repository()

    q_record = QueryHistoryRecord(
        query_id="q_test_777",
        query="What fine was imposed?",
        answer="A fine of ₹50,000 was imposed.",
        confidence_score=0.85,
        risk_level="MEDIUM_RISK",
        overall_warning="Verification advised for amount ₹50,000 due to OCR noise.",
        document_id="doc_chk_1",
        mode="confidence_aware",
        execution_time_ms=120.5,
    )
    q_repo.save_query(q_record)

    # Verify query fetch
    saved_q = q_repo.get_query("q_test_777")
    assert saved_q is not None
    assert saved_q.query == "What fine was imposed?"
    assert saved_q.risk_level == "MEDIUM_RISK"

    # Save evidence items
    ev_items = [
        EvidenceHistoryRecord(
            evidence_id="q_test_777_ev_0",
            query_id="q_test_777",
            document_id="doc_chk_1",
            document_name="Judgment.pdf",
            chunk_id="chk_001_test",
            page_number=1,
            evidence_text="court imposed a fine of ₹50,000",
            confidence=0.85,
            min_confidence=0.48,
            risk="MEDIUM",
            flagged=True,
            tokens=[
                EvidenceWord(text="fine", confidence=0.95, page=1, bbox=[100, 200, 130, 220]),
                EvidenceWord(text="of", confidence=0.94, page=1, bbox=[135, 200, 150, 220]),
                EvidenceWord(text="₹50,000", confidence=0.48, page=1, bbox=[155, 200, 210, 220], is_low_confidence=True),
            ],
            token_ids=["doc_chk_1_p1_t0", "doc_chk_1_p1_t1", "doc_chk_1_p1_t2"],
        )
    ]
    ev_repo.save_evidence_items(ev_items)

    # Fetch evidence by query
    fetched_ev = ev_repo.get_evidence_by_query("q_test_777")
    assert len(fetched_ev) == 1
    assert fetched_ev[0].evidence_text == "court imposed a fine of ₹50,000"
    assert fetched_ev[0].flagged is True
    assert len(fetched_ev[0].tokens) == 3
    assert fetched_ev[0].tokens[2].is_low_confidence is True


def test_evaluation_repository(setup_mock_mongodb):
    """Test EvaluationRepository persists and retrieves benchmark runs."""
    eval_repo = get_evaluation_repository()
    report = {
        "dataset": "Indian_Legal_Corpus",
        "baseline_rag": {"faithfulness": 0.61, "hallucination_rate": 0.39},
        "confidence_aware_rag": {"faithfulness": 0.94, "hallucination_rate": 0.06},
        "divergence_scenarios_tested": 15,
    }
    eval_repo.save_evaluation("benchmark_run_01", report)

    latest = eval_repo.get_latest_evaluation()
    assert latest is not None
    assert latest["dataset"] == "Indian_Legal_Corpus"
    assert latest["confidence_aware_rag"]["faithfulness"] == 0.94


def test_api_endpoints_with_mongodb(setup_mock_mongodb):
    """Integration test verifying FastAPI endpoints with MongoDB collections."""
    app = create_application()
    client = TestClient(app)

    # 1. Test documents list (empty initially)
    res = client.get("/api/v1/documents")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 2. Add document through repository
    doc_repo = get_document_repository()
    doc_repo.save_document(
        DocumentSummary(
            document_id="doc_api_test",
            filename="Test_Doc.pdf",
            pages=2,
            chunks=4,
            average_confidence=0.91,
            min_confidence=0.75,
            file_size_bytes=50000,
        )
    )

    # 3. Test GET /documents
    res = client.get("/api/v1/documents")
    assert res.status_code == 200
    docs = res.json()
    assert any(d["document_id"] == "doc_api_test" for d in docs)

    # 4. Test GET /documents/{id}
    res = client.get("/api/v1/documents/doc_api_test")
    assert res.status_code == 200
    assert res.json()["filename"] == "Test_Doc.pdf"

    # 5. Test GET /documents/{id}/pages
    res = client.get("/api/v1/documents/doc_api_test/pages")
    assert res.status_code == 200
    pages = res.json()
    assert len(pages) == 2

    # 6. Test GET /documents/{id}/pages/1
    res = client.get("/api/v1/documents/doc_api_test/pages/1")
    assert res.status_code == 200
    assert res.json()["page_number"] == 1

    # 7. Test Queries History Endpoint
    q_repo = get_query_repository()
    q_repo.save_query(
        QueryHistoryRecord(
            query_id="q_api_test",
            query="What is the test question?",
            answer="This is a test answer.",
            confidence_score=0.95,
            risk_level="LOW_RISK",
        )
    )
    res = client.get("/api/v1/queries")
    assert res.status_code == 200
    queries = res.json()
    assert any(q["query_id"] == "q_api_test" for q in queries)

    # 8. Test DELETE /documents/{id}
    res = client.delete("/api/v1/documents/doc_api_test")
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # Verify deleted in MongoDB
    assert setup_mock_mongodb[DOCUMENTS_COLLECTION].find_one({"_id": "doc_api_test"}) is None
