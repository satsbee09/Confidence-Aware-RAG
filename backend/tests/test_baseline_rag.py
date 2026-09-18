import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
import fitz
from app.main import app
from app.core.config import settings
from app.schemas.query import ComparisonResponse


@pytest.fixture
def degraded_pdf_bytes():
    """Create in-memory bytes of a degraded legal document."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    text = (
        "HIGH COURT OF DELHI - WRIT PETITION ORDER\n"
        "Petitioner: Surender Sharma vs Union of India\n"
        "Decision: Writ petition dismissed on 14 August 2024.\n"
        "Reason: Non-compliance with Section 420 statutory timeline.\n"
        "Costs assessed: Penalty of Rs. 25000 payable within 30 days."
    )
    page.insert_text((50, 70), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.mark.asyncio
async def test_compare_endpoint_side_by_side(degraded_pdf_bytes, tmp_path: Path, monkeypatch):
    """
    Verify /api/v1/compare runs both Baseline and Confidence-Aware pipelines
    on identical data and returns structured side-by-side comparison.
    """
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "storage")
    settings.ensure_directories()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Ingest document
        files = {"file": ("court_order_degraded.pdf", degraded_pdf_bytes, "application/pdf")}
        ingest_res = await client.post("/api/v1/ingest", files=files)
        assert ingest_res.status_code == 201
        doc_id = ingest_res.json()["document_id"]

        # Call compare endpoint
        compare_payload = {
            "query": "What was the penalty amount assessed?",
            "document_id": doc_id,
        }
        compare_res = await client.post("/api/v1/compare", json=compare_payload)
        assert compare_res.status_code == 200

        data = compare_res.json()
        assert "baseline" in data
        assert "confidence_aware" in data
        assert "key_difference" in data

        # Baseline verification: no warning
        assert data["baseline"]["warning"] is None
        assert "answer" in data["baseline"]
        assert len(data["baseline"]["sources"]) > 0

        # Confidence-Aware verification
        assert "answer" in data["confidence_aware"]
        assert data["confidence_aware"]["mode"] == "confidence_aware"
        assert data["confidence_aware"]["confidence_score"] > 0.0
        assert data["confidence_aware"]["risk_level"] in ["LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"]
