import re
import json
import os
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from loguru import logger

from app.core.config import settings
from app.schemas.evidence import EvidenceQualityReport, AnalyzedEvidenceChunk
from app.schemas.query import (
    SourceCitation,
    LLMStructuredOutput,
    QueryResponse,
)


class BaseLLMProvider(ABC):
    """
    Abstract Base Class for LLM Providers.
    Decouples answer generation from any specific cloud provider.
    """

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str) -> str:
        """Generate text completion given prompt and system instructions."""
        pass


class GroqLLMProvider(BaseLLMProvider):
    """
    Groq Cloud API provider utilizing ultra-fast Llama-3 and Qwen models.
    """

    FALLBACK_MODELS = [
        "openai/gpt-oss-120b",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-20b",
        "groq/compound-mini",
        "groq/compound",
    ]

    _cached_working_model: Optional[str] = None

    def __init__(self, api_key: Optional[str] = None, model: str = settings.LLM_MODEL):
        self.api_key = api_key or settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "")
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            from groq import Groq
            if not self.api_key:
                raise ValueError("GROQ_API_KEY is not configured in settings or environment.")
            self._client = Groq(api_key=self.api_key, timeout=12.0)
        return self._client

    def generate(self, prompt: str, system_prompt: str) -> str:
        client = self._get_client()
        
        # If we have a cached working model, prioritize it
        ordered_models = []
        if GroqLLMProvider._cached_working_model:
            ordered_models.append(GroqLLMProvider._cached_working_model)
        if self.model not in ordered_models:
            ordered_models.append(self.model)
        for m in self.FALLBACK_MODELS:
            if m not in ordered_models:
                ordered_models.append(m)

        last_error = None
        for m in ordered_models:
            # First try with JSON mode, then standard completion
            for use_json_mode in [True, False]:
                try:
                    logger.debug(f"Calling Groq API with model: {m} (json_mode: {use_json_mode})")
                    kwargs: Dict[str, Any] = {
                        "model": m,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": settings.LLM_TEMPERATURE,
                        "max_tokens": settings.LLM_MAX_TOKENS,
                    }
                    if use_json_mode:
                        kwargs["response_format"] = {"type": "json_object"}

                    response = client.chat.completions.create(**kwargs)
                    content = response.choices[0].message.content
                    if content and len(content.strip()) > 0:
                        GroqLLMProvider._cached_working_model = m
                        return content
                except Exception as e:
                    last_error = e
                    err_str = str(e).lower()
                    if "model_not_found" in err_str or "does not exist" in err_str or "404" in err_str:
                        break

        raise last_error or RuntimeError("All Groq model attempts failed.")


class OpenAILLMProvider(BaseLLMProvider):
    """
    OpenAI API Provider (GPT-4o, GPT-4o-mini).
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "The `openai` package is required for OpenAILLMProvider. "
                    "Install it using `pip install openai`."
                )
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY is not configured in settings or environment.")
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def generate(self, prompt: str, system_prompt: str) -> str:
        client = self._get_client()
        logger.debug(f"Calling OpenAI API with model: {self.model}")
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic rule-based Mock LLM Provider for offline testing, local dev,
    and fallback operation when cloud API access is unavailable.
    """

    def generate(self, prompt: str, system_prompt: str) -> str:
        logger.debug("Generating response using MockLLMProvider")

        has_warning = "HIGH_RISK" in prompt or "Warning" in prompt or "low confidence" in prompt.lower()
        pages = re.findall(r"\[Page\s+(\d+)\]", prompt)
        cited_pages = [int(p) for p in pages] if pages else [1]
        page_num = cited_pages[0]

        # Cleanly extract document evidence bodies (filtering out header labels and uncertain token notes)
        evidence_bodies = []
        raw_blocks = re.findall(r"Evidence\s+\d+.*?:\n(.*?)(?=\nUncertain Tokens|\n\nEvidence|\n\nEVIDENCE|\Z)", prompt, re.DOTALL)
        for raw_b in raw_blocks:
            clean_b = raw_b.strip()
            if clean_b:
                evidence_bodies.append(clean_b)

        combined_evidence = "\n\n".join(evidence_bodies) if evidence_bodies else prompt

        # Extract user query to tailor mock answer
        user_query = ""
        q_match = re.search(r"USER QUESTION:\s*(.*?)(?=\n\nDOCUMENT EVIDENCE|\Z)", prompt, re.DOTALL)
        if q_match:
            user_query = q_match.group(1).strip().lower()

        extracted_content = None

        # Intelligent section extraction for common queries
        if any(w in user_query for w in ["skill", "technical", "stack", "technology"]):
            s_match = re.search(r"(TECHNICAL SKILLS.*?(?=\n[A-Z\s]{4,}:|\nPROJECTS|\nEXPERIENCE|\nEDUCATION|\Z))", combined_evidence, re.DOTALL | re.IGNORECASE)
            if s_match:
                extracted_content = s_match.group(1).strip()
        elif any(w in user_query for w in ["education", "degree", "college", "school", "cgpa"]):
            e_match = re.search(r"(EDUCATION.*?(?=\n[A-Z\s]{4,}:|\nTECHNICAL SKILLS|\nPROJECTS|\Z))", combined_evidence, re.DOTALL | re.IGNORECASE)
            if e_match:
                extracted_content = e_match.group(1).strip()
        elif any(w in user_query for w in ["project", "built", "system", "aggregator"]):
            p_match = re.search(r"(PROJECTS.*?(?=\n[A-Z\s]{4,}:|\nACHIEVEMENTS|\nCERTIFICATIONS|\Z))", combined_evidence, re.DOTALL | re.IGNORECASE)
            if p_match:
                extracted_content = p_match.group(1).strip()

        if not extracted_content:
            if evidence_bodies:
                # Use first substantive 2-3 lines of evidence
                lines = [l.strip() for l in evidence_bodies[0].splitlines() if l.strip()]
                extracted_content = " ".join(lines[:3]) if lines else evidence_bodies[0][:300]
            else:
                extracted_content = "The requested information was found in the supporting document."

        if has_warning:
            answer = (
                f"Based on the document evidence [Page {page_num}]:\n\n{extracted_content}\n\n"
                f"Note: Certain tokens exhibit lower OCR clarity in the scan; verify critical details against the original document."
            )
            warning = "Supporting evidence contains low-confidence OCR text. Verify against the original document."
        else:
            answer = f"According to the official document [Page {page_num}]:\n\n{extracted_content}"
            warning = None

        sources = [
            {"page": p, "confidence": 0.55 if has_warning else 0.95, "flagged": has_warning}
            for p in sorted(list(set(cited_pages)))
        ]

        result_dict = {
            "answer": answer,
            "sources": sources,
            "overall_warning": warning,
        }
        return json.dumps(result_dict)


def get_llm_provider() -> BaseLLMProvider:
    """
    Factory function to select LLM provider based on settings and available API keys.
    Falls back gracefully to Mock provider if keys are missing.
    """
    provider_name = settings.LLM_PROVIDER.lower()

    if provider_name == "groq":
        if settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY"):
            return GroqLLMProvider()
        logger.warning("GROQ_API_KEY not found. Using MockLLMProvider for offline fallback.")
        return MockLLMProvider()

    if provider_name == "openai":
        if settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY"):
            return OpenAILLMProvider()
        logger.warning("OPENAI_API_KEY not found. Using MockLLMProvider for offline fallback.")
        return MockLLMProvider()

    return MockLLMProvider()


class PromptBuilder:
    """
    Constructs calibrated prompts with confidence annotations and explicit risk directives.
    """

    SYSTEM_PROMPT = (
        "You are an expert AI document intelligence assistant specialized in analyzing official legal, judicial, government, and technical documents.\n"
        "Your task is to answer the user question directly, accurately, and comprehensively using ONLY the provided document evidence.\n\n"
        "RULES FOR ACCURACY, HIGH CONFIDENCE, AND RISK CALIBRATION:\n"
        "1. Direct & Complete Answers: Directly answer what the user asked with clean, well-formatted Markdown (structured bullet points, bold headings, concise lists). Never include generic robotic preambles like 'Based on the provided document...'.\n"
        "2. Exact Page Citations: Every factual statement MUST cite the source page in brackets, e.g. [Page 1].\n"
        "3. High-Confidence Evidence: When OCR Quality is high (≥85%), deliver an authoritative, clear, and comprehensive answer.\n"
        "4. High-Risk / Uncertain Evidence Handling: When evidence contains FLAGGED or LOW-CONFIDENCE OCR tokens (e.g. uncertain figures, dates, or names), still provide the answer based on context, but explicitly qualify the uncertain tokens (e.g., '⚠️ Note: The token [X] has low OCR confidence ({conf}%), please verify with original scan').\n"
        "5. Output MUST be valid JSON adhering strictly to this schema:\n"
        "{\n"
        '  "answer": "Direct, structured markdown answer string with [Page X] citations.",\n'
        '  "sources": [{"page": 1, "confidence": 0.95, "flagged": false}],\n'
        '  "overall_warning": "Warning text if uncertain tokens are present, otherwise null"\n'
        "}"
    )

    @classmethod
    def build_user_prompt(
        cls,
        query: str,
        evidence_report: EvidenceQualityReport,
        is_baseline: bool = False,
    ) -> str:
        """
        Builds the user prompt payload.
        If is_baseline=True, confidence metadata and warning tags are stripped (Baseline RAG mode).
        """
        evidence_blocks = []
        for i, chunk in enumerate(evidence_report.analyzed_chunks, 1):
            if is_baseline:
                # Conventional RAG: Pure text without confidence signals
                block = f"Evidence {i} [Page {chunk.page}]:\n{chunk.chunk_text}"
            else:
                # Proposed: Confidence-aware context with token degradation warnings
                flag_status = "⚠️ FLAGGED (Low-Confidence OCR Tokens Detected)" if chunk.flagged else "✅ High Confidence"
                low_tokens = []
                for s in chunk.key_sentences:
                    for w in s.low_confidence_words:
                        low_tokens.append(f"'{w.text}' ({w.confidence*100:.0f}%)")
                
                low_tokens_str = ", ".join(low_tokens) if low_tokens else "None"

                block = (
                    f"Evidence {i} [Page {chunk.page}] (OCR Quality: {chunk.chunk_confidence*100:.1f}%, Status: {flag_status}):\n"
                    f"{chunk.chunk_text}\n"
                    f"Uncertain Tokens Requiring Caution: {low_tokens_str}"
                )
            evidence_blocks.append(block)

        formatted_evidence = "\n\n".join(evidence_blocks)

        prompt = (
            f"USER QUESTION:\n{query}\n\n"
            f"DOCUMENT EVIDENCE:\n{formatted_evidence}\n\n"
            f"EVIDENCE QUALITY ASSESSMENT:\n"
            f"- Overall Risk Level: {evidence_report.overall_risk_level}\n"
            f"- Overall Evidence Confidence: {evidence_report.overall_confidence*100:.1f}%\n"
            f"- Flagged Sentence Count: {evidence_report.flagged_count}\n\n"
            f"Respond ONLY with valid JSON containing 'answer', 'sources', and 'overall_warning' keys."
        )
        return prompt


class ConfidenceAwareLLMService:
    """
    Main LLM Orchestration Service.
    Handles prompt construction, provider calls, JSON extraction, and Pydantic response validation.
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider or get_llm_provider()

    def _extract_json(self, raw_response: str) -> Dict[str, Any]:
        """
        Safely extracts and normalizes JSON dictionary from LLM string output.
        """
        clean_text = raw_response.strip()

        # Strip ```json ... ``` code fences
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]

        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        clean_text = clean_text.strip()

        parsed: Optional[Dict[str, Any]] = None
        try:
            parsed = json.loads(clean_text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", clean_text, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                except Exception:
                    pass

        # If LLM didn't return a JSON object, wrap raw text as answer
        if not isinstance(parsed, dict):
            return {
                "answer": clean_text if clean_text else "Information retrieved from document.",
                "sources": [],
                "overall_warning": None,
            }

        # Normalize keys if 'answer' is missing or formatted as list/dict
        raw_ans = parsed.get("answer")
        if isinstance(raw_ans, list):
            parsed["answer"] = "\n".join(f"• {item}" if isinstance(item, str) else str(item) for item in raw_ans)
        elif isinstance(raw_ans, dict):
            parsed["answer"] = "\n".join(f"**{k}**: {v}" for k, v in raw_ans.items())
        elif not raw_ans or not isinstance(raw_ans, str):
            parts = []
            for k, v in parsed.items():
                if k not in ["sources", "overall_warning", "warning"]:
                    parts.append(f"{k.capitalize()}: {v}")
            parsed["answer"] = "\n".join(parts) if parts else str(parsed)

        # Normalize sources
        normalized_sources = []
        raw_sources = parsed.get("sources", [])
        if isinstance(raw_sources, list):
            for item in raw_sources:
                if isinstance(item, dict) and "page" in item:
                    try:
                        page_num = int(item["page"])
                        conf = float(item.get("confidence", 0.95))
                        flag = bool(item.get("flagged", False))
                        normalized_sources.append({
                            "page": max(1, page_num),
                            "confidence": min(1.0, max(0.0, conf)),
                            "flagged": flag,
                        })
                    except Exception:
                        pass
                elif isinstance(item, int):
                    normalized_sources.append({
                        "page": max(1, item),
                        "confidence": 0.90,
                        "flagged": False,
                    })
        parsed["sources"] = normalized_sources

        return parsed

    def generate_answer(
        self,
        query: str,
        evidence_report: EvidenceQualityReport,
        is_baseline: bool = False,
    ) -> QueryResponse:
        """
        Generate a validated, confidence-aware answer grounded in document evidence.
        """
        system_prompt = PromptBuilder.SYSTEM_PROMPT
        user_prompt = PromptBuilder.build_user_prompt(
            query=query,
            evidence_report=evidence_report,
            is_baseline=is_baseline,
        )

        try:
            raw_output = self.provider.generate(user_prompt, system_prompt)
            data = self._extract_json(raw_output)
            structured_data = LLMStructuredOutput(**data)
            answer_text = structured_data.answer
            sources = structured_data.sources
            warning = structured_data.overall_warning or evidence_report.warning_message
        except Exception as e:
            logger.warning(f"Structured LLM call error: {e}. Executing offline mock generator fallback.")
            try:
                raw_output = MockLLMProvider().generate(user_prompt, system_prompt)
                data = self._extract_json(raw_output)
                structured_data = LLMStructuredOutput(**data)
                answer_text = structured_data.answer
                sources = structured_data.sources
                warning = structured_data.overall_warning or evidence_report.warning_message
            except Exception as e2:
                logger.error(f"Fallback generation error: {e2}")
                first_chunk = evidence_report.analyzed_chunks[0] if evidence_report.analyzed_chunks else None
                page_num = first_chunk.page if first_chunk else 1
                answer_text = (
                    f"Based on available document evidence [Page {page_num}], "
                    f"the document provides relevant details: {first_chunk.chunk_text if first_chunk else ''}"
                )
                sources = [
                    SourceCitation(
                        page=page_num,
                        confidence=evidence_report.overall_confidence,
                        flagged=evidence_report.overall_risk_level == "HIGH_RISK",
                    )
                ]
                warning = evidence_report.warning_message

        # Enrich sources with physical OCR bounding boxes and document metadata from analyzed chunks
        from app.repositories.document_repository import get_document_repository
        doc_repo = get_document_repository()

        # Build lookup map from page -> analyzed chunk & sentences
        page_to_chunk = {}
        for ac in evidence_report.analyzed_chunks:
            if ac.page not in page_to_chunk:
                page_to_chunk[ac.page] = ac

        enriched_sources: List[SourceCitation] = []
        seen_chunk_ids = set()

        def build_citation(matching_chunk, default_conf: float = 0.95) -> SourceCitation:
            doc_id = matching_chunk.doc_id if matching_chunk else None
            doc_name = None
            if doc_id:
                doc_obj = doc_repo.get_document(doc_id)
                if doc_obj:
                    doc_name = doc_obj.filename

            ev_text = None
            tokens_list = []
            risk_label = "LOW"
            if matching_chunk:
                key_sents = matching_chunk.key_sentences
                if key_sents:
                    seen_tokens = set()
                    sent_texts = []
                    any_flagged = False
                    total_conf = 0.0
                    token_count = 0

                    for ks in key_sents:
                        sent_texts.append(ks.sentence_text)
                        if ks.flagged:
                            any_flagged = True
                        for w in (ks.all_words or []):
                            tok_key = (w.text, round(w.bbox[0], 1), round(w.bbox[1], 1)) if w.bbox else w.text
                            if tok_key not in seen_tokens:
                                seen_tokens.add(tok_key)
                                tokens_list.append(w)
                                total_conf += w.confidence
                                token_count += 1

                    ev_text = " ".join(sent_texts)
                    avg_conf = (total_conf / token_count) if token_count > 0 else matching_chunk.chunk_confidence
                    if any_flagged or matching_chunk.flagged:
                        risk_label = "HIGH"
                    elif avg_conf < 0.85:
                        risk_label = "MEDIUM"
                else:
                    ev_text = matching_chunk.chunk_text[:250]
                    risk_label = "HIGH" if matching_chunk.flagged else ("MEDIUM" if matching_chunk.chunk_confidence < 0.85 else "LOW")
                    tokens_list = getattr(matching_chunk, "words", []) or []

            return SourceCitation(
                page=matching_chunk.page if matching_chunk else 1,
                confidence=matching_chunk.chunk_confidence if matching_chunk else default_conf,
                flagged=matching_chunk.flagged if matching_chunk else (risk_label == "HIGH"),
                chunk_id=matching_chunk.chunk_id if matching_chunk else None,
                document_id=doc_id,
                document_name=doc_name or (f"Document_{doc_id[:6]}.pdf" if doc_id else "Document.pdf"),
                evidence_text=ev_text,
                risk=risk_label,
                tokens=tokens_list,
                page_width=float(getattr(matching_chunk, "page_width", None) or 595.0) if matching_chunk else 595.0,
                page_height=float(getattr(matching_chunk, "page_height", None) or 842.0) if matching_chunk else 842.0,
            )

        # 1. Primary sources cited by model
        for src in (sources or []):
            matching_chunk = page_to_chunk.get(src.page)
            if not matching_chunk and evidence_report.analyzed_chunks:
                matching_chunk = evidence_report.analyzed_chunks[0]

            if matching_chunk and matching_chunk.chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(matching_chunk.chunk_id)
                enriched_sources.append(build_citation(matching_chunk, default_conf=src.confidence))

        # 2. Add high-value supporting evidence chunks (limit to top 2-3 most relevant sources total)
        for ac in evidence_report.analyzed_chunks:
            if ac.chunk_id not in seen_chunk_ids and (ac.similarity >= 0.50 or ac.final_score >= 0.50):
                if len(enriched_sources) < 3:
                    seen_chunk_ids.add(ac.chunk_id)
                    enriched_sources.append(build_citation(ac, default_conf=ac.chunk_confidence))

        if not enriched_sources:
            if evidence_report.analyzed_chunks:
                top_ac = evidence_report.analyzed_chunks[0]
                enriched_sources.append(build_citation(top_ac, default_conf=top_ac.chunk_confidence))
            else:
                enriched_sources = [
                    SourceCitation(page=1, confidence=evidence_report.overall_confidence, flagged=False)
                ]

        # Derive separate semantic relevance and optical confidence scores
        sem_sim = round(max((c.similarity for c in evidence_report.analyzed_chunks if c.similarity > 0), default=0.95), 4)
        ocr_conf = round(evidence_report.overall_confidence, 4)
        
        conf_score = evidence_report.overall_confidence
        risk_level = evidence_report.overall_risk_level
        mode_label = "baseline" if is_baseline else "confidence_aware"

        return QueryResponse(
            query=query,
            answer=answer_text,
            confidence_score=round(conf_score, 4),
            semantic_similarity=sem_sim,
            ocr_confidence=ocr_conf,
            risk_level=risk_level,
            sources=enriched_sources,
            overall_warning=warning,
            evidence_report=evidence_report,
            mode=mode_label,
            execution_time_ms=0.0,
        )


# Singleton LLM Service Provider
_llm_service_instance: Optional[ConfidenceAwareLLMService] = None


def get_llm_service() -> ConfidenceAwareLLMService:
    """Returns singleton ConfidenceAwareLLMService instance."""
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = ConfidenceAwareLLMService()
    return _llm_service_instance
