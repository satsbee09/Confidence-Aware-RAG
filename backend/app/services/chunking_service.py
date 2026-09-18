import re
import uuid
from typing import List, Tuple, Dict, Any, Optional
from loguru import logger

from app.core.config import settings
from app.schemas.ocr import OCRDocument, OCRPage, OCRWord, OCRLine
from app.schemas.chunk import Chunk


class ConfidenceAwareChunker:
    """
    Sentence-boundary aware chunker that aggregates OCR words and propagates
    hierarchical optical confidence with low-confidence word penalties.
    """

    def __init__(
        self,
        min_tokens: int = settings.CHUNK_MIN_TOKENS,
        max_tokens: int = settings.CHUNK_MAX_TOKENS,
        overlap_tokens: int = settings.CHUNK_OVERLAP_TOKENS,
        low_conf_threshold: float = settings.LOW_CONFIDENCE_THRESHOLD,
    ):
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.low_conf_threshold = low_conf_threshold

    def _estimate_token_count(self, text: str) -> int:
        """Estimate token count (approx 1.3 words per token or whitespace split)."""
        words = text.strip().split()
        return max(1, int(len(words) * 1.25))

    def _split_into_sentences(self, page: OCRPage) -> List[Tuple[str, List[OCRWord]]]:
        """
        Split page lines and words into coherent sentence units preserving word provenance.
        """
        sentences: List[Tuple[str, List[OCRWord]]] = []
        current_sentence_words: List[OCRWord] = []
        sentence_end_pattern = re.compile(r"[\.!\?;:\n]$")

        # Flatten words in reading order
        page_words = page.words

        if not page_words:
            # Fallback if page has lines but words weren't populated
            for line in page.lines:
                for w in line.words:
                    page_words.append(w)

        for word in page_words:
            current_sentence_words.append(word)
            # Check for sentence terminal punctuation
            if sentence_end_pattern.search(word.text) or len(current_sentence_words) >= 30:
                sent_text = " ".join(w.text for w in current_sentence_words).strip()
                if sent_text:
                    sentences.append((sent_text, list(current_sentence_words)))
                current_sentence_words = []

        # Remaining words
        if current_sentence_words:
            sent_text = " ".join(w.text for w in current_sentence_words).strip()
            if sent_text:
                sentences.append((sent_text, list(current_sentence_words)))

        return sentences

    def _calculate_chunk_metrics(
        self, words: List[OCRWord]
    ) -> Tuple[float, float, float, List[OCRWord]]:
        """
        Computes raw weighted average confidence, minimum confidence,
        low-confidence words, and the penalized effective confidence score.
        """
        if not words:
            return 1.0, 1.0, 1.0, []

        total_char_weight = sum(len(w.text) for w in words)
        if total_char_weight > 0:
            raw_conf = sum(w.confidence * len(w.text) for w in words) / total_char_weight
        else:
            raw_conf = sum(w.confidence for w in words) / len(words)

        min_conf = min(w.confidence for w in words)
        low_conf_words = [w for w in words if w.confidence < self.low_conf_threshold]
        low_conf_ratio = len(low_conf_words) / len(words)

        # Penalize confidence if critical words have very low recognition probability
        # Penalty increases with both proportion of noisy words and severity of lowest word
        penalty = (0.4 * low_conf_ratio) + (0.2 * (1.0 - min_conf))
        penalized_conf = raw_conf * max(0.0, 1.0 - penalty)
        penalized_conf = max(0.0, min(1.0, penalized_conf))

        return (
            round(raw_conf, 4),
            round(min_conf, 4),
            round(penalized_conf, 4),
            low_conf_words,
        )

    def create_chunks(self, document: OCRDocument) -> List[Chunk]:
        """
        Partition an OCRDocument into confidence-aware text chunks.
        """
        all_chunks: List[Chunk] = []
        doc_sentences: List[Tuple[str, List[OCRWord], int, float, float]] = []  # (text, words, page, width, height)

        # Collect sentences across all pages
        for page in document.pages:
            p_w = float(page.width) if page.width else 595.0
            p_h = float(page.height) if page.height else 842.0
            page_sentences = self._split_into_sentences(page)
            for sent_text, sent_words in page_sentences:
                doc_sentences.append((sent_text, sent_words, page.page, p_w, p_h))

        if not doc_sentences:
            logger.warning(f"Document {document.doc_id} yielded no sentences for chunking.")
            return []

        # Sliding window over sentences
        current_sentences: List[str] = []
        current_words: List[OCRWord] = []
        current_pages: set = set()
        chunk_idx = 1

        i = 0
        while i < len(doc_sentences):
            sent_text, sent_words, page_num, p_w, p_h = doc_sentences[i]
            current_sentences.append(sent_text)
            current_words.extend(sent_words)
            current_pages.add(page_num)

            chunk_text = " ".join(current_sentences)
            token_count = self._estimate_token_count(chunk_text)

            # If chunk reached target size or reached end of document
            if token_count >= self.min_tokens or i == len(doc_sentences) - 1:
                # Determine primary page by majority word count in chunk
                page_counts: Dict[int, int] = {}
                for w in current_words:
                    page_counts[w.page] = page_counts.get(w.page, 0) + 1
                primary_page = max(page_counts, key=page_counts.get) if page_counts else (min(current_pages) if current_pages else 1)

                # Compute weighted and penalized confidence metrics
                raw_conf, min_conf, penalized_conf, low_conf_words = self._calculate_chunk_metrics(
                    current_words
                )

                chunk_obj = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=document.doc_id,
                    chunk_text=chunk_text,
                    confidence_score=penalized_conf,
                    raw_confidence=raw_conf,
                    min_confidence=min_conf,
                    page=primary_page,
                    page_range=sorted(list(current_pages)),
                    page_width=p_w,
                    page_height=p_h,
                    token_count=token_count,
                    words=current_words,
                    low_confidence_words=low_conf_words,
                    metadata={
                        "chunk_index": chunk_idx,
                        "filename": document.filename,
                        "sentence_count": len(current_sentences),
                    },
                )
                all_chunks.append(chunk_obj)
                chunk_idx += 1

                # Sliding window step with overlap: keep trailing sentences approximating overlap_tokens
                overlap_words_acc: List[OCRWord] = []
                overlap_sents_acc: List[str] = []
                overlap_pages_acc: set = set()

                for back_sent, back_words, back_page, _bw, _bh in reversed(
                    doc_sentences[max(0, i - 3) : i + 1]
                ):
                    back_text = " ".join(reversed([back_sent] + overlap_sents_acc))
                    if self._estimate_token_count(back_text) <= self.overlap_tokens:
                        overlap_sents_acc.insert(0, back_sent)
                        overlap_words_acc = back_words + overlap_words_acc
                        overlap_pages_acc.add(back_page)
                    else:
                        break

                current_sentences = overlap_sents_acc
                current_words = overlap_words_acc
                current_pages = overlap_pages_acc

            i += 1

        logger.info(
            f"Document '{document.filename}' chunked into {len(all_chunks)} chunks. "
            f"Avg Chunk Conf: {sum(c.confidence_score for c in all_chunks)/max(1, len(all_chunks)):.4f}"
        )
        return all_chunks
