import time
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query
from loguru import logger

from app.schemas.query import QueryRequest, QueryResponse, ComparisonResponse, BaselineAnswer
from app.schemas.db_models import QueryHistoryRecord, EvidenceHistoryRecord
from app.services.retrieval_service import get_retrieval_service
from app.services.evidence_service import get_evidence_service
from app.services.llm_service import get_llm_service
from app.repositories import (
    get_vector_store,
    get_query_repository,
    get_evidence_repository,
)

router = APIRouter()


@router.post(
    "/query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query Document with Confidence-Aware RAG",
    description=(
        "Executes a natural language query against indexed documents. "
        "Retrieves candidates, applies confidence reranking, analyzes token-level evidence quality, "
        "generates a grounded answer, and persists query & evidence records into MongoDB Atlas."
    ),
)
async def query_pipeline(request: QueryRequest) -> QueryResponse:
    """
    Complete Query Pipeline:
    Query -> Vector Retrieval -> Confidence Reranking -> Evidence Quality Analysis ->
    Confidence-Aware LLM -> Persist to MongoDB (queries & evidence) -> Return response.
    """
    start_time = time.perf_counter()
    query_text = request.query.strip()

    if not query_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query text cannot be empty.",
        )

    vector_store = get_vector_store()
    if vector_store.count() == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vector store is empty. Please upload and ingest a document first.",
        )

    logger.info(
        f"Processing query: '{query_text}' (doc_id: {request.document_id}, "
        f"confidence_reranking: {request.use_confidence_reranking})"
    )

    try:
        # 1. Semantic Retrieval + Confidence Reranking
        retrieval_service = get_retrieval_service()
        retrieval_result = retrieval_service.retrieve(
            query=query_text,
            doc_id=request.document_id,
            use_confidence_reranking=request.use_confidence_reranking,
        )

        if not retrieval_result.top_candidates:
            empty_res = QueryResponse(
                query=query_text,
                answer="No relevant document evidence was found to answer this question.",
                confidence_score=0.0,
                risk_level="HIGH_RISK",
                sources=[],
                overall_warning="No matching document sections found in the vector index.",
                mode="confidence_aware" if request.use_confidence_reranking else "baseline",
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
            )
            # Save query record
            q_id = str(uuid.uuid4())
            get_query_repository().save_query(
                QueryHistoryRecord(
                    query_id=q_id,
                    query=query_text,
                    answer=empty_res.answer,
                    confidence_score=0.0,
                    risk_level="HIGH_RISK",
                    overall_warning=empty_res.overall_warning,
                    document_id=request.document_id,
                    mode=empty_res.mode,
                    execution_time_ms=empty_res.execution_time_ms,
                )
            )
            return empty_res

        # 2. Evidence Quality Analysis (Sentence relevance & token confidence inspection)
        evidence_service = get_evidence_service()
        evidence_report = evidence_service.analyze_evidence(
            query=query_text,
            candidates=retrieval_result.top_candidates,
        )

        # 3. Confidence-Aware LLM Generation
        llm_service = get_llm_service()
        query_response = llm_service.generate_answer(
            query=query_text,
            evidence_report=evidence_report,
            is_baseline=not request.use_confidence_reranking,
        )

        # Record total execution time
        total_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        query_response.execution_time_ms = total_latency_ms

        # 4. Persist Query & Evidence into MongoDB
        query_id = str(uuid.uuid4())
        try:
            query_repo = get_query_repository()
            evidence_repo = get_evidence_repository()

            retrieved_chunk_ids = [c.chunk.chunk_id for c in retrieval_result.top_candidates]
            query_record = QueryHistoryRecord(
                query_id=query_id,
                query=query_text,
                answer=query_response.answer,
                confidence_score=query_response.confidence_score,
                risk_level=query_response.risk_level,
                overall_warning=query_response.overall_warning,
                model=getattr(llm_service, "model_name", "groq/compound-mini"),
                document_id=request.document_id,
                retrieved_chunks=retrieved_chunk_ids,
                source_count=len(query_response.sources),
                mode=query_response.mode,
                execution_time_ms=total_latency_ms,
            )
            query_repo.save_query(query_record)

            evidence_items = []
            for src_idx, src in enumerate(query_response.sources):
                ev_id = f"{query_id}_ev_{src_idx}"
                ev_rec = EvidenceHistoryRecord(
                    evidence_id=ev_id,
                    query_id=query_id,
                    document_id=src.document_id,
                    document_name=src.document_name,
                    chunk_id=src.chunk_id,
                    page_number=src.page,
                    evidence_text=src.evidence_text or "",
                    confidence=src.confidence,
                    min_confidence=src.confidence,
                    risk=src.risk or "LOW",
                    flagged=src.flagged,
                    tokens=src.tokens,
                    token_ids=[f"{src.document_id}_p{src.page}_t{i}" for i in range(len(src.tokens))],
                    page_width=src.page_width or 595.0,
                    page_height=src.page_height or 842.0,
                )
                evidence_items.append(ev_rec)

            evidence_repo.save_evidence_items(evidence_items)
        except Exception as persist_err:
            logger.warning(f"Note on query/evidence MongoDB persistence: {persist_err}")

        logger.info(
            f"Query answered in {total_latency_ms}ms. Risk: {query_response.risk_level}, "
            f"Confidence: {query_response.confidence_score:.2f} (Query ID: {query_id})"
        )
        return query_response

    except Exception as e:
        logger.error(f"Error during query execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during query processing: {str(e)}",
        )


@router.get(
    "/queries",
    response_model=List[QueryHistoryRecord],
    status_code=status.HTTP_200_OK,
    summary="Get Query History",
    description="Returns a list of recent queries, generated answers, risk levels, and execution latencies from MongoDB.",
)
async def get_query_history(limit: int = Query(default=50, ge=1, le=200)) -> List[QueryHistoryRecord]:
    """Retrieve history of past user queries from MongoDB."""
    query_repo = get_query_repository()
    return query_repo.list_queries(limit=limit)


@router.get(
    "/queries/{query_id}",
    response_model=QueryHistoryRecord,
    status_code=status.HTTP_200_OK,
    summary="Get Query Details",
    description="Retrieve full details for a specific query execution ID.",
)
async def get_query_by_id(query_id: str) -> QueryHistoryRecord:
    """Retrieve metadata for a specific query."""
    query_repo = get_query_repository()
    record = query_repo.get_query(query_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query with ID '{query_id}' not found.",
        )
    return record


@router.get(
    "/queries/{query_id}/evidence",
    response_model=List[EvidenceHistoryRecord],
    status_code=status.HTTP_200_OK,
    summary="Get Query Evidence Items",
    description="Retrieve all supporting evidence items, bounding boxes, and risk tags associated with a specific query.",
)
async def get_query_evidence(query_id: str) -> List[EvidenceHistoryRecord]:
    """Retrieve evidence records linked to a query."""
    evidence_repo = get_evidence_repository()
    return evidence_repo.get_evidence_by_query(query_id)


@router.post(
    "/compare",
    response_model=ComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Side-by-Side Comparison (Baseline RAG vs Confidence-Aware RAG)",
    description=(
        "Executes the query through BOTH Baseline RAG (no confidence propagation) "
        "and Proposed Confidence-Aware RAG on the identical document and retrieval pool. "
        "Demonstrates how Confidence-Aware RAG detects and flags OCR noise while Baseline fails silently."
    ),
)
async def compare_pipelines(request: QueryRequest) -> ComparisonResponse:
    """
    Executes identical query on identical document across both pipelines simultaneously.
    """
    query_text = request.query.strip()
    if not query_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query text cannot be empty.",
        )

    vector_store = get_vector_store()
    if vector_store.count() == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vector store is empty. Please upload and ingest a document first.",
        )

    retrieval_service = get_retrieval_service()
    evidence_service = get_evidence_service()
    llm_service = get_llm_service()

    # --- 1. BASELINE RAG EXECUTION ---
    t_base_start = time.perf_counter()
    baseline_retrieval = retrieval_service.retrieve(
        query=query_text,
        doc_id=request.document_id,
        use_confidence_reranking=False,
    )
    baseline_report = evidence_service.analyze_evidence(
        query=query_text,
        candidates=baseline_retrieval.top_candidates,
    )
    baseline_llm_res = llm_service.generate_answer(
        query=query_text,
        evidence_report=baseline_report,
        is_baseline=True,
    )
    t_base_latency = round((time.perf_counter() - t_base_start) * 1000, 2)

    top_chunk_sim = (
        baseline_retrieval.top_candidates[0].similarity
        if baseline_retrieval.top_candidates
        else 0.0
    )
    baseline_pages = [s.page for s in baseline_llm_res.sources]

    baseline_answer_obj = BaselineAnswer(
        answer=baseline_llm_res.answer,
        sources=baseline_pages,
        top_chunk_similarity=round(top_chunk_sim, 4),
        warning=None,  # Conventional RAG never assesses or warns about OCR noise
        latency_ms=t_base_latency,
    )

    # --- 2. PROPOSED CONFIDENCE-AWARE RAG EXECUTION ---
    t_prop_start = time.perf_counter()
    prop_retrieval = retrieval_service.retrieve(
        query=query_text,
        doc_id=request.document_id,
        use_confidence_reranking=True,
    )
    prop_report = evidence_service.analyze_evidence(
        query=query_text,
        candidates=prop_retrieval.top_candidates,
    )
    prop_res = llm_service.generate_answer(
        query=query_text,
        evidence_report=prop_report,
        is_baseline=False,
    )
    prop_res.execution_time_ms = round((time.perf_counter() - t_prop_start) * 1000, 2)

    # Summarize Key Divergence
    if prop_res.risk_level == "HIGH_RISK":
        difference_summary = (
            "Baseline RAG generated an answer with false certainty without checking OCR quality. "
            "Confidence-Aware RAG detected low-confidence tokens in supporting evidence and explicitly "
            "communicated uncertainty with a verification recommendation."
        )
    else:
        difference_summary = (
            "Both systems retrieved high-confidence evidence. "
            "Confidence-Aware RAG confirmed OCR optical reliability (Confidence: "
            f"{prop_res.confidence_score*100:.1f}%), verifying that the cited evidence is solid."
        )

    return ComparisonResponse(
        query=query_text,
        document_id=request.document_id,
        baseline=baseline_answer_obj,
        confidence_aware=prop_res,
        key_difference=difference_summary,
    )
