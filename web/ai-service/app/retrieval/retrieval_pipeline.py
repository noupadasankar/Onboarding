"""Retrieval pipeline — thin stateless wrapper used by the API layer.

Provides a single ``run()`` coroutine that the API calls.
Keeps the API handler free of pipeline wiring.
"""
from __future__ import annotations

from app.models.retrieval_result import RetrievalResult
from app.retrieval.retrieval_service import RetrievalConfig, RetrievalService


class RetrievalPipeline:
    """Wraps RetrievalService with default dependency wiring.

    Intended for use as a FastAPI dependency or standalone call.

    Args:
        service: Pre-configured RetrievalService. If None, a default is built
            using the process-wide VectorService singleton.
    """

    def __init__(self, service: RetrievalService | None = None) -> None:
        self._service = service

    def _get_service(self) -> RetrievalService:
        if self._service is not None:
            return self._service
        # Lazy default — builds using singletons
        from app.services.vector_service import get_vector_service
        return RetrievalService(vector_service=get_vector_service())

    async def run(
        self,
        query: str,
        config: RetrievalConfig | None = None,
    ) -> RetrievalResult:
        """Run the full retrieval pipeline and return a RetrievalResult."""
        return await self._get_service().retrieve(query, config)
