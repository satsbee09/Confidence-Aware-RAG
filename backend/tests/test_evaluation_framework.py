"""
Unit and Integration Tests for Phase 10: Evaluation Framework & Document Degradation.
"""

import pytest
import json
from pathlib import Path
from PIL import Image
import fitz

from evaluation.degrade_document import DocumentDegrader, create_sample_legal_documents
from evaluation.evaluate import RAGEvaluator
from app.core.config import settings


@pytest.fixture
def sample_test_image():
    """Create a simple test image in memory."""
    img = Image.new("RGB", (300, 300), color="white")
    return img


def test_document_degrader_filters(sample_test_image):
    """Verify each degradation filter operates without error and preserves dimensions."""
    degrader = DocumentDegrader()

    # 1. Blur
    blurred = degrader.add_gaussian_blur(sample_test_image, radius=1.0)
    assert blurred.size == sample_test_image.size

    # 2. Salt and Pepper Noise
    noisy = degrader.add_salt_and_pepper_noise(sample_test_image, amount=0.02)
    assert noisy.size == sample_test_image.size

    # 3. Contrast / Fading
    faded = degrader.add_contrast_and_fading(sample_test_image, contrast=0.7, brightness=1.1)
    assert faded.size == sample_test_image.size

    # 4. JPEG Compression
    compressed = degrader.add_jpeg_compression(sample_test_image, quality=30)
    assert compressed.size == sample_test_image.size

    # 5. Skew
    skewed = degrader.add_skew(sample_test_image, angle=2.0)
    assert skewed.size == sample_test_image.size

    # 6. Full degradation tiers
    for tier in ["clean", "low", "medium", "high"]:
        deg = degrader.degrade_image(sample_test_image, level=tier)
        assert deg.size == sample_test_image.size


def test_create_sample_legal_documents(tmp_path: Path):
    """Verify creation of ground truth Indian legal documents."""
    docs = create_sample_legal_documents(tmp_path)
    assert len(docs) >= 2
    for doc in docs:
        assert Path(doc["clean_pdf"]).exists()
        assert len(doc["facts"]) > 0


def test_evaluator_query_and_metrics(tmp_path: Path, monkeypatch):
    """Verify RAGEvaluator computes accurate comparison metrics between pipelines."""
    # Setup temporary questions and storage
    test_storage = tmp_path / "eval_storage"
    test_clean_dir = tmp_path / "clean"
    test_results = tmp_path / "results" / "benchmark.json"

    monkeypatch.setattr(settings, "STORAGE_DIR", test_storage)
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path / "uploads")
    settings.ensure_directories()

    # Create 1 sample document
    docs = create_sample_legal_documents(test_clean_dir)
    pdf_path = docs[0]["clean_pdf"]

    questions_data = [
        {
            "id": "t1",
            "doc_ref": docs[0]["clean_pdf"].stem,
            "question": "What is the penalty or cost amount?",
            "key_facts": ["25,000", "Rs. 25,000"],
            "vulnerable_tokens": ["25,000"],
            "critical_type": "monetary_penalty",
        }
    ]
    q_file = tmp_path / "questions.json"
    with open(q_file, "w", encoding="utf-8") as f:
        json.dump(questions_data, f)

    evaluator = RAGEvaluator(
        questions_file=q_file,
        output_results_file=test_results,
        storage_dir=test_storage,
    )

    doc_id = evaluator.ingest_pdf(pdf_path)
    assert doc_id is not None

    res = evaluator.evaluate_query(questions_data[0], doc_id)
    assert "baseline" in res
    assert "proposed" in res
    assert res["baseline"]["fact_accuracy"] >= 0.0
    assert res["proposed"]["fact_accuracy"] >= 0.0
