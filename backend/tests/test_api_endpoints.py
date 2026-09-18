import io
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
import fitz  # PyMuPDF
from app.main import app
from app.core.config import settings


@pytest.fixture
def sample_pdf_bytes():
    """Create in-memory bytes of a sample RTI reply PDF."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    text = (
        "GOVERNMENT OF INDIA - MINISTRY OF REVENUE\n"
        "RTI ACT REPLY - FILE NO: RTI/DEL/2025/110\n\n"
        "Subject: Land acquisition and sanction order details.\n"
        "Decision: The application was rejected on 12 June 2025 by competent authority.\n"
        "Reason: Failure to provide required Form 4-A valuation certificate.\n"
        "Fine Imposed: Total penalty of Rs. 50000 assessed under Section 19(8)(b)."
    )
    page.insert_text((50, 70), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.mark.asyncio
async def test_full_api_lifecycle(sample_pdf_bytes, tmp_path: Path, monkeypatch):
    """
    Test complete API workflow:
    1. Ingest PDF -> POST /api/v1/ingest
    2. List documents -> GET /api/v1/documents
    3. Query document -> POST /api/v1/query
    4. Delete document -> DELETE /api/v1/documents/{doc_id}
    """
    # Point upload and storage to tmp_path for test isolation
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    settings.ensure_directories()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test Ingest PDF
        files = {"file": ("rti_reply_2025.pdf", sample_pdf_bytes, "application/pdf")}
        ingest_res = await client.post("/api/v1/ingest", files=files)
        assert ingest_res.status_code == 201
        ingest_data = ingest_res.json()
        assert ingest_data["status"] == "success"
        doc_id = ingest_data["document_id"]
        assert ingest_data["filename"] == "rti_reply_2025.pdf"
        assert ingest_data["pages"] == 1
        assert ingest_data["chunks"] >= 1
        assert ingest_data["average_confidence"] > 0.80

        # 2. Test GET /documents
        docs_res = await client.get("/api/v1/documents")
        assert docs_res.status_code == 200
        docs_list = docs_res.json()
        assert len(docs_list) >= 1
        matching_doc = next(d for d in docs_list if d["document_id"] == doc_id)
        assert matching_doc["filename"] == "rti_reply_2025.pdf"

        # 3. Test GET /documents/{doc_id}
        single_doc_res = await client.get(f"/api/v1/documents/{doc_id}")
        assert single_doc_res.status_code == 200
        assert single_doc_res.json()["document_id"] == doc_id

        # 4. Test POST /query (Confidence-Aware Mode)
        query_payload = {
            "query": "What was the reason for rejecting the application?",
            "document_id": doc_id,
            "use_confidence_reranking": True,
        }
        query_res = await client.post("/api/v1/query", json=query_payload)
        assert query_res.status_code == 200
        query_data = query_res.json()
        assert "answer" in query_data
        assert query_data["mode"] == "confidence_aware"
        assert len(query_data["sources"]) > 0
        assert query_data["confidence_score"] > 0.0

        # 5. Test POST /query (Baseline Mode)
        baseline_payload = {
            "query": "What was the fine imposed?",
            "document_id": doc_id,
            "use_confidence_reranking": False,
        }
        baseline_res = await client.post("/api/v1/query", json=baseline_payload)
        assert baseline_res.status_code == 200
        assert baseline_res.json()["mode"] == "baseline"

        # 5b. Test GET /documents/{doc_id}/pages/1/image
        img_res = await client.get(f"/api/v1/documents/{doc_id}/pages/1/image")
        assert img_res.status_code == 200
        assert img_res.headers["content-type"] == "image/png"
        assert len(img_res.content) > 100
        assert "X-Page-Width" in img_res.headers

        # Test invalid page
        invalid_img_res = await client.get(f"/api/v1/documents/{doc_id}/pages/999/image")
        assert invalid_img_res.status_code == 404

        # 6. Test DELETE /documents/{doc_id}
        del_res = await client.delete(f"/api/v1/documents/{doc_id}")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "success"

        # Verify document is gone
        get_deleted_res = await client.get(f"/api/v1/documents/{doc_id}")
        assert get_deleted_res.status_code == 404


@pytest.mark.asyncio
async def test_ingest_invalid_file_type():
    """Verify rejection of non-document file types."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("malicious_script.exe", b"binary content", "application/octet-stream")}
        res = await client.post("/api/v1/ingest", files=files)
        assert res.status_code == 400
        assert "Unsupported file format" in res.json()["detail"]


@pytest.mark.asyncio
async def test_query_empty_text():
    """Verify validation error on empty query string."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/query", json={"query": "   "})
        assert res.status_code == 400
