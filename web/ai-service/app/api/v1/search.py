"""Search / retrieval API endpoint.

POST /api/v1/search
  Accept a user query, run the full retrieval pipeline, and return the
  assembled context, prompt, and citations.

No LLM call happens here.  That is Increment 8.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import RequestContext, authenticated_request
from app.retrieval.retrieval_pipeline import RetrievalPipeline
from app.retrieval.retrieval_service import RetrievalConfig
from app.retrieval.query_processor import QueryProcessingError
from app.schemas.search import SearchRequest, SearchResponse
from app.services.vector_service import VectorService, get_vector_service
from app.retrieval.retrieval_service import RetrievalService

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse, status_code=200)
async def search(
    body: SearchRequest,
    ctx: RequestContext = Depends(authenticated_request),
    vector_service: VectorService = Depends(get_vector_service),
) -> SearchResponse:
    """Retrieve the most relevant HR document chunks for *body.query*.

    Pipeline:
      1. Normalise query.
      2. Embed query with the configured embedding provider.
      3. Semantic search in ChromaDB (top_k_search=20).
      4. Rerank to top_k results.
      5. Assemble context within token budget.
      6. Build a grounded prompt.
      7. Return context, prompt, and citations.
    """
    retrieval_service = RetrievalService(vector_service=vector_service)
    pipeline = RetrievalPipeline(service=retrieval_service)

    # SECURITY: department scope comes from the authenticated request context
    # (set by Node.js from the verified JWT / RBAC layer), NOT from the request
    # body.  This prevents a caller from querying another department's documents
    # by spoofing the body.department field.
    config = RetrievalConfig(
        top_k_search=20,
        top_k_rerank=body.top_k,
        min_score=body.min_score,
        department=ctx.department,   # ← enforced from X-User-Department header
        document_id=body.document_id,
        section=body.section,
        use_hybrid=body.use_hybrid,
    )

    try:
        result = await pipeline.run(body.query, config)
    except QueryProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Retrieval pipeline error: {exc}",
        ) from exc

    return SearchResponse(
        query=result.query,
        chunks_found=result.chunks_found,
        context=result.context,
        prompt=result.prompt,
        citations=result.citations,
        context_token_count=result.context_token_count,
    )
