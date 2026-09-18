import pytest
import json
from app.schemas.evidence import (
    EvidenceWord,
    EvidenceSentence,
    AnalyzedEvidenceChunk,
    EvidenceQualityReport,
)
from app.schemas.query import QueryResponse, LLMStructuredOutput
from app.services.llm_service import (
    BaseLLMProvider,
    MockLLMProvider,
    PromptBuilder,
    ConfidenceAwareLLMService,
)


def _build_sample_evidence_report(flagged: bool = False) -> EvidenceQualityReport:
    """Helper to build sample evidence report for tests."""
    words = [
        EvidenceWord(text="Application", confidence=0.95, page=4),
        EvidenceWord(text="rejected", confidence=0.52 if flagged else 0.96, page=4, is_low_confidence=flagged),
        EvidenceWord(text="on", confidence=0.98, page=4),
        EvidenceWord(text="12/06/2025.", confidence=0.41 if flagged else 0.95, page=4, is_low_confidence=flagged),
    ]

    sent = EvidenceSentence(
        sentence_text="Application rejected on 12/06/2025.",
        sentence_confidence=0.54 if flagged else 0.96,
        similarity_to_query=0.88,
        flagged=flagged,
        low_confidence_words=[w for w in words if w.is_low_confidence],
        all_words=words,
    )

    chunk = AnalyzedEvidenceChunk(
        chunk_id="c_test_1",
        doc_id="doc_rti",
        page=4,
        page_range=[4],
        chunk_text="Application rejected on 12/06/2025.",
        chunk_confidence=0.60 if flagged else 0.96,
        key_sentences=[sent],
        flagged=flagged,
        min_word_confidence=0.41 if flagged else 0.95,
    )

    return EvidenceQualityReport(
        query="Why was the application rejected?",
        analyzed_chunks=[chunk],
        overall_confidence=0.54 if flagged else 0.96,
        overall_risk_level="HIGH_RISK" if flagged else "LOW_RISK",
        flagged_count=1 if flagged else 0,
        warning_message="The supporting evidence contains low-confidence OCR text. Verify against the original document."
        if flagged
        else None,
    )


def test_prompt_builder_includes_confidence_and_tokens():
    """Verify PromptBuilder constructs rich prompt with confidence metadata."""
    report = _build_sample_evidence_report(flagged=True)
    prompt = PromptBuilder.build_user_prompt(
        query="Why was the application rejected?",
        evidence_report=report,
        is_baseline=False,
    )

    assert "USER QUESTION:" in prompt
    assert "DOCUMENT EVIDENCE:" in prompt
    assert "[Page 4]" in prompt
    assert "FLAGGED" in prompt
    assert "12/06/2025." in prompt
    assert "HIGH_RISK" in prompt


def test_mock_llm_provider_generation():
    """Verify MockLLMProvider produces valid JSON matching schema."""
    provider = MockLLMProvider()
    report = _build_sample_evidence_report(flagged=True)
    prompt = PromptBuilder.build_user_prompt("When was it rejected?", report)

    raw_output = provider.generate(prompt, PromptBuilder.SYSTEM_PROMPT)
    data = json.loads(raw_output)

    assert "answer" in data
    assert "sources" in data
    assert len(data["sources"]) > 0
    assert data["sources"][0]["page"] == 4
    assert data["overall_warning"] is not None


def test_llm_service_end_to_end():
    """Verify ConfidenceAwareLLMService parses output and returns QueryResponse."""
    llm_service = ConfidenceAwareLLMService(provider=MockLLMProvider())
    report = _build_sample_evidence_report(flagged=True)

    response = llm_service.generate_answer(
        query="When was the application rejected?",
        evidence_report=report,
        is_baseline=False,
    )

    assert isinstance(response, QueryResponse)
    assert response.confidence_score == 0.54
    assert response.risk_level == "HIGH_RISK"
    assert response.overall_warning is not None
    assert len(response.sources) == 1
    assert response.sources[0].page == 4
    assert response.sources[0].flagged is True
    assert response.mode == "confidence_aware"


def test_llm_service_graceful_fallback():
    """Verify graceful fallback if LLM produces raw plain text instead of JSON."""
    class BrokenLLMProvider(BaseLLMProvider):
        def generate(self, prompt: str, system_prompt: str) -> str:
            return "Plain text unformatted response without JSON."

    llm_service = ConfidenceAwareLLMService(provider=BrokenLLMProvider())
    report = _build_sample_evidence_report(flagged=True)

    response = llm_service.generate_answer(
        query="What happened?",
        evidence_report=report,
    )

    assert isinstance(response, QueryResponse)
    assert response.risk_level == "HIGH_RISK"
    assert response.confidence_score == 0.54
    assert len(response.sources) > 0
