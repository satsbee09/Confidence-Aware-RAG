import re
from typing import List, Tuple, Optional
import numpy as np
from loguru import logger

from app.core.config import settings
from app.schemas.chunk import Chunk
from app.schemas.ocr import OCRWord
from app.schemas.retrieval import ScoredChunk
from app.schemas.evidence import (
    EvidenceWord,
    EvidenceSentence,
    AnalyzedEvidenceChunk,
    EvidenceQualityReport,
)
from app.services.embedding_service import BaseEmbeddingService, get_embedding_service


class EvidenceQualityService:
    """
    Analyzes retrieved chunks at the sentence and token level to identify
    OCR reliability risks in supporting evidence.
    """

    def __init__(
        self,
        embedding_service: Optional[BaseEmbeddingService] = None,
        evidence_threshold: float = settings.EVIDENCE_CONFIDENCE_THRESHOLD,
        top_n: int = settings.TOP_N_EVIDENCE,
    ):
        self.embedding_service = embedding_service or get_embedding_service()
        self.evidence_threshold = evidence_threshold
        self.top_n = top_n

    def _split_chunk_words_into_sentences(
        self, chunk: Chunk
    ) -> List[Tuple[str, List[OCRWord]]]:
        """
        Segment chunk text into natural logical sentences/units and map constituent OCR words.
        Handles technical section headers, bullet lists, and decimal numbers without premature splits.
        """
        sentences: List[Tuple[str, List[OCRWord]]] = []
        if not chunk.words:
            if chunk.chunk_text.strip():
                raw_sents = re.split(r"(?<=[.!?])\s+", chunk.chunk_text.strip())
                for s in raw_sents:
                    if s.strip():
                        dummy_words = [
                            OCRWord(text=tok, confidence=chunk.confidence_score, page=chunk.page)
                            for tok in s.split()
                        ]
                        sentences.append((s.strip(), dummy_words))
            return sentences

        section_headers = {
            "TECHNICAL", "SKILLS", "EDUCATION", "PROJECTS", "EXPERIENCE",
            "CERTIFICATIONS", "ACHIEVEMENTS", "SUMMARY", "PROFESSIONAL",
            "SECTION", "ORDER", "JUDGMENT", "PETITIONER", "RESPONDENT"
        }

        current_words: List[OCRWord] = []
        for i, word in enumerate(chunk.words):
            current_words.append(word)
            txt = word.text.strip()

            # Check if next word marks a major section boundary
            next_is_header = False
            if i + 1 < len(chunk.words):
                next_word_txt = chunk.words[i + 1].text.strip()
                if next_word_txt.isupper() and len(next_word_txt) >= 3 and next_word_txt in section_headers:
                    next_is_header = True

            is_period_end = (
                txt.endswith(".")
                and not re.search(r"\b\d+\.\d*$", txt)
                and not any(txt.endswith(ext) for ext in [".js", ".com", ".org", ".io", ".ai", ".net"])
                and len(txt) > 2
            )
            is_punct_end = txt.endswith("!") or txt.endswith("?")

            if (is_period_end or is_punct_end or next_is_header or len(current_words) >= 50) and len(current_words) >= 4:
                sent_text = " ".join(w.text for w in current_words).strip()
                if sent_text:
                    sentences.append((sent_text, list(current_words)))
                current_words = []

        if current_words:
            sent_text = " ".join(w.text for w in current_words).strip()
            if sent_text:
                sentences.append((sent_text, list(current_words)))

        return sentences

    def analyze_evidence(
        self,
        query: str,
        candidates: List[ScoredChunk],
        top_n: Optional[int] = None,
    ) -> EvidenceQualityReport:
        """
        Perform token-level and sentence-level evidence quality analysis on top retrieved candidates.
        """
        n = top_n or self.top_n
        top_candidates = candidates[:n]

        if not top_candidates:
            logger.warning("Evidence analysis called with 0 candidates.")
            return EvidenceQualityReport(
                query=query,
                analyzed_chunks=[],
                overall_confidence=0.0,
                overall_risk_level="HIGH_RISK",
                flagged_count=0,
                warning_message="No supporting evidence found.",
            )

        from app.services.retrieval_service import normalize_query, compute_lexical_overlap
        cleaned_query = normalize_query(query)
        query_tokens = (cleaned_query or query).split()
        query_vec = self.embedding_service.encode_text(cleaned_query or query)
        analyzed_chunks: List[AnalyzedEvidenceChunk] = []
        all_key_sentence_confs: List[float] = []
        total_flagged_sentences = 0

        for scored_item in top_candidates:
            chunk = scored_item.chunk
            sentence_pairs = self._split_chunk_words_into_sentences(chunk)

            if not sentence_pairs:
                continue

            sent_texts = [pair[0] for pair in sentence_pairs]
            sent_embeddings = self.embedding_service.encode_batch(sent_texts)

            # Compute hybrid similarity of each sentence in chunk to query
            dense_sims = np.dot(sent_embeddings, query_vec)
            hybrid_sims = []
            for idx, s_txt in enumerate(sent_texts):
                d_sim = float(max(0.0, min(1.0, dense_sims[idx])))
                l_sim = compute_lexical_overlap(query_tokens, s_txt)
                h_sim = max(d_sim, (d_sim * 0.5) + (l_sim * 0.5))
                if l_sim > 0.6:
                    h_sim = max(h_sim, 0.8 + (0.2 * l_sim))
                hybrid_sims.append(h_sim)

            hybrid_sims_arr = np.array(hybrid_sims)

            # Rank sentences by hybrid query relevance
            ranked_sentence_indices = list(np.argsort(-hybrid_sims_arr))

            # Precision selection: pick only the highest-scoring key sentences that directly answer the query
            max_sim = float(hybrid_sims_arr[ranked_sentence_indices[0]]) if ranked_sentence_indices else 0.0
            selected_indices = []
            
            # Select top sentences that meet high relevance criteria (max 2 sentences per chunk)
            for idx in ranked_sentence_indices:
                sim_val = float(hybrid_sims_arr[idx])
                # Must be at least 0.45 relevance and within 80% of top sentence
                if sim_val >= max(0.45, max_sim * 0.80):
                    selected_indices.append(idx)
                if len(selected_indices) >= 2:
                    break

            # Fallback: if no sentence exceeded 0.45, select only the single best sentence
            if not selected_indices and ranked_sentence_indices:
                selected_indices = [ranked_sentence_indices[0]]

            selected_indices = sorted(selected_indices)  # preserve natural reading order

            key_sentences: List[EvidenceSentence] = []
            chunk_is_flagged = False
            chunk_min_word_conf = 1.0

            for s_idx in selected_indices:
                s_text, s_words = sentence_pairs[s_idx]
                s_sim = float(max(0.0, min(1.0, hybrid_sims_arr[s_idx])))

                evidence_words: List[EvidenceWord] = []
                low_conf_words: List[EvidenceWord] = []

                for w in s_words:
                    # Only flag substantive alphanumeric words (skip standalone punctuation/bullets)
                    has_alphanumeric = any(c.isalnum() for c in w.text)
                    is_low = (w.confidence < self.evidence_threshold) and has_alphanumeric
                    ev_word = EvidenceWord(
                        text=w.text,
                        confidence=w.confidence,
                        page=w.page,
                        bbox=w.bbox,
                        is_low_confidence=is_low,
                    )
                    evidence_words.append(ev_word)
                    if is_low:
                        low_conf_words.append(ev_word)
                        chunk_is_flagged = True

                    if w.confidence < chunk_min_word_conf:
                        chunk_min_word_conf = w.confidence

                s_conf = (
                    sum(w.confidence for w in evidence_words) / len(evidence_words)
                    if evidence_words
                    else chunk.confidence_score
                )
                s_flagged = len(low_conf_words) > 0

                if s_flagged:
                    total_flagged_sentences += 1

                all_key_sentence_confs.append(s_conf)

                key_sentences.append(
                    EvidenceSentence(
                        sentence_text=s_text,
                        sentence_confidence=round(s_conf, 4),
                        similarity_to_query=round(s_sim, 4),
                        flagged=s_flagged,
                        low_confidence_words=low_conf_words,
                        all_words=evidence_words,
                    )
                )

            analyzed_chunk = AnalyzedEvidenceChunk(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                page=chunk.page,
                page_range=chunk.page_range or [chunk.page],
                page_width=getattr(chunk, "page_width", 595.0),
                page_height=getattr(chunk, "page_height", 842.0),
                chunk_text=chunk.chunk_text,
                chunk_confidence=chunk.confidence_score,
                similarity=round(scored_item.similarity, 4),
                final_score=round(scored_item.final_score, 4),
                key_sentences=key_sentences,
                flagged=chunk_is_flagged,
                min_word_confidence=round(chunk_min_word_conf, 4),
            )
            analyzed_chunks.append(analyzed_chunk)

        # Calculate aggregate evidence statistics
        if all_key_sentence_confs:
            overall_conf = sum(all_key_sentence_confs) / len(all_key_sentence_confs)
        else:
            overall_conf = sum(c.chunk.confidence_score for c in top_candidates) / len(
                top_candidates
            )

        # Determine calibrated risk classification
        if total_flagged_sentences > 0 or overall_conf < self.evidence_threshold:
            risk_level = "HIGH_RISK"
            warning = (
                "Warning: Supporting evidence contains low-confidence OCR text (e.g. uncertain dates, "
                "monetary amounts, sections, or names). Verification against original document is recommended."
            )
        elif overall_conf < 0.85:
            risk_level = "MEDIUM_RISK"
            warning = (
                "Notice: Supporting evidence exhibits moderate OCR confidence. "
                "Please verify critical legal provisions or figures."
            )
        else:
            risk_level = "LOW_RISK"
            warning = None

        logger.info(
            f"Evidence analysis complete. Overall Conf: {overall_conf:.4f}, "
            f"Risk Level: {risk_level}, Flagged Sentences: {total_flagged_sentences}"
        )

        return EvidenceQualityReport(
            query=query,
            analyzed_chunks=analyzed_chunks,
            overall_confidence=round(overall_conf, 4),
            overall_risk_level=risk_level,
            flagged_count=total_flagged_sentences,
            warning_message=warning,
        )


# Singleton Evidence Service Provider
_evidence_service_instance: Optional[EvidenceQualityService] = None


def get_evidence_service() -> EvidenceQualityService:
    """Returns singleton EvidenceQualityService instance."""
    global _evidence_service_instance
    if _evidence_service_instance is None:
        _evidence_service_instance = EvidenceQualityService()
    return _evidence_service_instance
