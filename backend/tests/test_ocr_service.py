import pytest
from pathlib import Path
from PIL import Image, ImageDraw
import fitz  # PyMuPDF
from app.schemas.ocr import OCRWord, OCRLine, OCRPage, OCRDocument
from app.services.ocr_service import OCRService, DigitalPDFEngine


def test_ocr_word_confidence_clamping():
    """Verify confidence clamping and 0-100 to 0.0-1.0 normalization."""
    # Percentage input (e.g., 95.5 from Tesseract)
    word1 = OCRWord(text="Section", confidence=95.5, page=1, bbox=[10, 10, 50, 30])
    assert word1.confidence == 0.955
    assert word1.text == "Section"

    # Standard float
    word2 = OCRWord(text="420", confidence=0.72, page=1, bbox=[55, 10, 90, 30])
    assert word2.confidence == 0.72

    # Out-of-bounds float
    word3 = OCRWord(text="IPC", confidence=1.5, page=1, bbox=[95, 10, 120, 30])
    assert word3.confidence == 0.015  # normalized from 1.5%


def test_synthetic_pdf_ocr_processing(tmp_path: Path):
    """Create a synthetic 2-page legal document PDF and test OCR pipeline."""
    pdf_path = tmp_path / "sample_rti_reply.pdf"

    # Create synthetic multi-page PDF using PyMuPDF
    doc = fitz.open()

    # Page 1: RTI Header and Query
    page1 = doc.new_page(width=595, height=842)
    p1_text = (
        "RIGHT TO INFORMATION ACT 2005 - REPLY\n"
        "Department of Revenue, Government of India\n"
        "Application Reference Number: RTI/2025/DEL/9841\n"
        "Applicant: Ramesh Kumar\n"
        "Subject: Information regarding land acquisition sanction in Plot 42-B."
    )
    page1.insert_text((50, 80), p1_text, fontsize=12)

    # Page 2: Sanction Order and Decision
    page2 = doc.new_page(width=595, height=842)
    p2_text = (
        "ORDER AND DECISION DETAILS\n"
        "The application was rejected on 12 June 2025 by competent authority.\n"
        "Reason for rejection: Non-submission of Form 4-A and valuation certificate.\n"
        "Total fine assessed: INR 50000 under Section 19(8)(b)."
    )
    page2.insert_text((50, 80), p2_text, fontsize=12)

    doc.save(pdf_path)
    doc.close()

    # Test processing through OCRService
    ocr_service = OCRService(engine_override="digital")
    result = ocr_service.process_pdf(pdf_path)

    assert isinstance(result, OCRDocument)
    assert result.total_pages == 2
    assert len(result.pages) == 2
    assert len(result.all_words) > 20
    assert result.average_confidence >= 0.90
    assert "RIGHT TO INFORMATION" in result.full_text
    assert "rejected on 12 June 2025" in result.full_text
    assert result.pages[0].page == 1
    assert result.pages[1].page == 2


def test_ocr_page_error_resilience(tmp_path: Path, monkeypatch):
    """Verify that a single page failure does not crash document ingestion."""
    pdf_path = tmp_path / "corrupt_test.pdf"
    doc = fitz.open()
    doc.new_page(width=595, height=842).insert_text((50, 50), "Page 1 Valid Text", fontsize=12)
    doc.new_page(width=595, height=842).insert_text((50, 50), "Page 2 Valid Text", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    ocr_service = OCRService(engine_override="digital")

    # Simulate an error on page 2
    original_extract = ocr_service.engine.extract_from_pdf_page

    def mock_extract(page_obj, page_number):
        if page_number == 2:
            raise RuntimeError("Simulated corrupt page rendering")
        return original_extract(page_obj, page_number)

    monkeypatch.setattr(ocr_service.engine, "extract_from_pdf_page", mock_extract)

    result = ocr_service.process_pdf(pdf_path)
    assert result.total_pages == 2
    assert result.pages[0].error is None
    assert result.pages[0].text != ""
    assert result.pages[1].error == "Simulated corrupt page rendering"
    assert result.pages[1].text == ""
