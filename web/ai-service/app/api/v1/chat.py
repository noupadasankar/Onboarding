"""POST /api/v1/chat — LangGraph multi-agent RAG chat endpoint (Increment 9).

Routes questions through the Supervisor → HR Agent (or Fallback) LangGraph
workflow. Supports both JSON and SSE streaming response modes.

The frontend contract is unchanged from Increment 8.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.chat.conversation_repository import get_conversation_repository
from app.core.security import RequestContext, authenticated_request
from app.graphs.supervisor_graph import GraphRunner
from app.llm.llm_factory import create_llm_provider
from app.llm.llm_service import LLMService
from app.llm.providers.base_provider import LLMAuthError, LLMProviderError
from app.retrieval.query_processor import QueryProcessingError
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.vector_service import VectorService, get_vector_service

router = APIRouter(tags=["chat"])


def _graph_runner(
    vector_service: VectorService = Depends(get_vector_service),
) -> GraphRunner:
    """FastAPI dependency — builds a GraphRunner for the current request."""
    llm = LLMService(provider=create_llm_provider())
    repo = get_conversation_repository()
    return GraphRunner(
        vector_service=vector_service,
        llm_service=llm,
        conv_repo=repo,
    )


@router.post("/chat", response_model=ChatResponse, status_code=200)
async def chat(
    body: ChatRequest,
    ctx: RequestContext = Depends(authenticated_request),
    runner: GraphRunner = Depends(_graph_runner),
) -> ChatResponse:
    """Answer a question through the LangGraph Supervisor → HR Agent workflow.

    Flow:
      1. Supervisor Agent selects the appropriate domain agent.
      2. HR Agent retrieves relevant document chunks from ChromaDB.
      3. HR Agent builds a grounded prompt and calls the LLM.
      4. Conversation is persisted.
      5. Response returned with answer, citations, and token usage.
    """
    if body.stream:
        return await _stream_response(body, ctx, runner)

    try:
        response = await runner.run(
            request=body,
            user_id=ctx.user_id,
            tenant=ctx.tenant,
        )
    except QueryProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except LLMAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM authentication error: {exc}",
        ) from exc
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM provider error: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {exc}",
        ) from exc

    return response


async def _stream_response(
    body: ChatRequest,
    ctx: RequestContext,
    runner: GraphRunner,
) -> StreamingResponse:
    """Run the graph and stream the answer token by token as SSE."""
    import json
    from app.chat.stream_handler import token_stream_to_sse

    # Run the full graph (non-streaming) then stream the answer word by word.
    # True token streaming from the LLM through LangGraph requires additional
    # infrastructure (LangGraph streaming mode) — this approach is pragmatic
    # and delivers an acceptable UX while keeping the graph stateless.
    try:
        response = await runner.run(request=body, user_id=ctx.user_id, tenant=ctx.tenant)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    async def _word_iter():
        for word in response.answer.split(" "):
            yield word + " "

    async def _event_gen():
        async for chunk in token_stream_to_sse(_word_iter(), response.conversation_id):
            yield chunk
        # Send metadata event at the end
        yield (
            "event: metadata\n"
            "data: " + json.dumps({
                "conversation_id": response.conversation_id,
                "model": response.model,
                "provider": response.provider,
                "citations": [c.model_dump() for c in response.citations],
                "usage": response.usage.model_dump(),
            }) + "\n\n"
        )

    return StreamingResponse(_event_gen(), media_type="text/event-stream")
