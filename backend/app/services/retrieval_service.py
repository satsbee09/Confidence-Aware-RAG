import time
import re
from typing import List, Tuple, Optional, Set
from loguru import logger

from app.core.config import settings
from app.schemas.chunk import Chunk
from app.schemas.retrieval import ScoredChunk, RetrievalResult
from app.services.embedding_service import BaseEmbeddingService, get_embedding_service
from app.repositories.vector_store import BaseVectorStore, get_vector_store


def normalize_query(query: str) -> str:
    """
    Cleans and normalizes query text, resolving joined words, camelCase,
    and common OCR/user typos to maximize embedding and retrieval accuracy.
    """
    if not query:
        return ""

    # 1. Split camelCase e.g., 'technicalSkills' -> 'technical Skills'
    q = re.sub(r"([a-z])([A-Z])", r"\1 \2", query)

    # 2. Split common stuck prefixes e.g. 'thetechnical' -> 'the technical', 'whatis' -> 'what is'
    prefixes = [
        "the", "what", "is", "are", "my", "your", "his", "her",
        "show", "get", "list", "give", "tell", "explain", "detail", "find"
    ]
    for p in prefixes:
        # Match prefix at beginning of word followed by at least 3 letters
        q = re.sub(rf"\b({p})([a-zA-Z]{{3,}})\b", r"\1 \2", q, flags=re.IGNORECASE)

    # 3. Correct common domain/resume/legal typos
    typo_map = {
        "skils": "skills",
        "skil": "skill",
        "techncal": "technical",
        "tehnical": "technical",
        "techincal": "technical",
        "experiance": "experience",
        "expereince": "experience",
        "eduction": "education",
        "eduation": "education",
        "certifcate": "certificate",
        "certifcates": "certificates",
        "certifications": "certifications",
        "projcts": "projects",
        "projct": "project",
        "achivements": "achievements",
        "achivement": "achievement",
        "penality": "penalty",
        "judgement": "judgment",
        "responsdent": "respondent",
        "patitioner": "petitioner",
        "petioner": "petitioner",
    }

    tokens = q.split()
    normalized_tokens = [typo_map.get(t.lower(), t) for t in tokens]
    return " ".join(normalized_tokens)


def compute_lexical_overlap(query_tokens: List[str], text: str) -> float:
    """
    Computes lexical similarity score between query tokens and chunk text.
    Gives special weight to exact matches, phrase matches, and section headers.
    """
    if not query_tokens or not text:
        return 0.0

    lower_text = text.lower()
    stopwords = {"what", "is", "are", "the", "a", "an", "of", "in", "for", "to", "and", "or", "on", "with", "by", "at", "from", "as", "this", "that", "these", "those", "it", "its"}
    key_tokens = [t.lower() for t in query_tokens if len(t) > 1 and t.lower() not in stopwords]

    if not key_tokens:
        key_tokens = [t.lower() for t in query_tokens if len(t) > 1]

    if not key_tokens:
        return 0.0

    # Token match ratio
    matched_count = 0
    for tok in key_tokens:
        if tok in lower_text:
            matched_count += 1
            # Bonus if token appears uppercase or as header e.g. "TECHNICAL SKILLS"
            if tok.upper() in text:
                matched_count += 0.5

    # Check for multi-word phrase match (e.g. "technical skills", "data structures")
    phrase = " ".join(key_tokens)
    phrase_bonus = 0.0
    if len(key_tokens) >= 2 and phrase in lower_text:
        phrase_bonus = 0.4

    base_ratio = matched_count / len(key_tokens)
    score = min(1.0, (base_ratio * 0.7) + phrase_bonus)
    return float(score)


class RetrievalService:
    """
    Service responsible for semantic retrieval and confidence-based reranking.
    Propagates OCR confidence into retrieval scoring to prioritize trustworthy evidence.
    """

    def __init__(
        self,
        embedding_service: Optional[BaseEmbeddingService] = None,
        vector_store: Optional[BaseVectorStore] = None,
        similarity_weight: float = settings.SIMILARITY_WEIGHT,
        confidence_weight: float = settings.CONFIDENCE_WEIGHT,
        top_k: int = settings.TOP_K,
    ):
        self.embedding_service = embedding_service or get_embedding_service()
        self._vector_store = vector_store
        self.similarity_weight = similarity_weight
        self.confidence_weight = confidence_weight
        self.top_k = top_k

    @property
    def vector_store(self) -> BaseVectorStore:
        return self._vector_store or get_vector_store()

    def calculate_rerank_score(self, similarity: float, ocr_confidence: float) -> float:
        """
        Compute the composite reranking score:
        final_score = similarity * (w_s + w_c * confidence)
        """
        bounded_sim = max(0.0, min(1.0, similarity))
        bounded_conf = max(0.0, min(1.0, ocr_confidence))

        multiplier = self.similarity_weight + (self.confidence_weight * bounded_conf)
        final_score = bounded_sim * multiplier
        return round(float(final_score), 4)

    def retrieve(
        self,
        query: str,
        doc_id: Optional[str] = None,
        top_k: Optional[int] = None,
        use_confidence_reranking: bool = True,
    ) -> RetrievalResult:
        """
        Execute hybrid semantic search followed by optional confidence reranking.

        Args:
            query: User search query
            doc_id: Optional document ID to filter search
            top_k: Number of candidates to retrieve
            use_confidence_reranking: If True, sort by composite final_score.
                                      If False (Baseline), sort purely by similarity.
        """
        start_time = time.perf_counter()
        k = top_k or self.top_k

        # Clean and normalize query for robust embedding and lexical retrieval
        cleaned_query = normalize_query(query)
        logger.info(
            f"Retrieving for query: '{query[:60]}' (normalized: '{cleaned_query[:60]}', "
            f"doc_id: {doc_id}, top_k: {k}, confidence_reranking: {use_confidence_reranking})"
        )

        # 1. Generate query embedding on cleaned query
        query_embedding = self.embedding_service.encode_text(cleaned_query or query)
        query_tokens = (cleaned_query or query).split()

        # 2. Semantic vector search (retrieve candidate pool)
        # Fetch up to 3x candidates to allow diverse hybrid scoring
        fetch_k = min(self.vector_store.count(), max(k, k * 3))
        raw_candidates: List[Tuple[Chunk, float]] = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=fetch_k,
            doc_id=doc_id,
        )

        if not raw_candidates:
            logger.warning("Vector store returned 0 candidates for query.")
            return RetrievalResult(
                query=query,
                doc_id=doc_id,
                candidates_retrieved=0,
                top_candidates=[],
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )

        # 3. Score candidates with Hybrid Dense + Lexical matching
        scored_items: List[ScoredChunk] = []
        for chunk, dense_sim in raw_candidates:
            clamped_dense_sim = max(0.0, min(1.0, dense_sim))
            lexical_sim = compute_lexical_overlap(query_tokens, chunk.chunk_text)

            # Hybrid blend: 55% dense semantic + 45% lexical keyword/section match
            hybrid_sim = max(clamped_dense_sim, (clamped_dense_sim * 0.55) + (lexical_sim * 0.45))
            if lexical_sim > 0.7:
                # Strong exact match on key section headers (e.g. TECHNICAL SKILLS)
                hybrid_sim = max(hybrid_sim, 0.75 + (0.25 * lexical_sim))

            hybrid_sim = max(0.0, min(1.0, hybrid_sim))
            conf = chunk.confidence_score

            if use_confidence_reranking:
                final_score = self.calculate_rerank_score(hybrid_sim, conf)
            else:
                # Baseline: final_score is simply the similarity
                final_score = hybrid_sim

            scored_items.append(
                ScoredChunk(
                    chunk=chunk,
                    similarity=round(hybrid_sim, 4),
                    ocr_confidence=round(conf, 4),
                    final_score=round(final_score, 4),
                    rank=1,
                )
            )

        # 4. Sort according to final_score descending
        scored_items.sort(key=lambda item: item.final_score, reverse=True)

        # Assign final rank indices and take top_k
        top_results = scored_items[:k]
        for rank_idx, item in enumerate(top_results, start=1):
            item.rank = rank_idx

        latency = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Retrieval complete in {latency:.2f}ms. Returned {len(top_results)} candidates."
        )

        return RetrievalResult(
            query=query,
            doc_id=doc_id,
            candidates_retrieved=len(raw_candidates),
            top_candidates=top_results,
            execution_time_ms=round(latency, 2),
        )


# Singleton Retrieval Service Provider
_retrieval_service_instance: Optional[RetrievalService] = None


def get_retrieval_service(reset: bool = False) -> RetrievalService:
    """Returns singleton RetrievalService instance."""
    global _retrieval_service_instance
    if _retrieval_service_instance is None or reset:
        _retrieval_service_instance = RetrievalService()
    return _retrieval_service_instance



