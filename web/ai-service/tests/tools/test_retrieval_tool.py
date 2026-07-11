"""Tests for RetrievalTool and CitationTool."""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.retrieval_result import Citation
from app.tools.citation_tool import citations_to_dicts, dicts_to_citations
from app.tools.retrieval_tool import RetrievalResult, RetrievalTool


class TestCitationTool:
    def test_to_dicts_preserves_fields(self) -> None:
        c = Citation(document="handbook.pdf", page=5, section="Leave", chunk_id="c1", score=0.91)
        d = citations_to_dicts([c])[0]
        assert d["document"] == "handbook.pdf"
        assert d["page"] == 5
        assert d["section"] == "Leave"

    def test_score_rounded_to_4dp(self) -> None:
        c = Citation(document="a.pdf", score=0.912345, chunk_id="x")
        d = citations_to_dicts([c])[0]
        assert d["score"] == 0.9123

    def test_empty_list(self) -> None:
        assert citations_to_dicts([]) == []

    def test_round_trip(self) -> None:
        c = Citation(document="a.pdf", page=3, section="S", chunk_id="c1", score=0.85)
        restored = dicts_to_citations(citations_to_dicts([c]))
        assert len(restored) == 1
        assert restored[0].document == "a.pdf"

    def test_dicts_to_citations_empty(self) -> None:
        assert dicts_to_citations([]) == []


class TestRetrievalToolUnit:
    """Tests using a mocked VectorService — no Chroma required."""

    def _make_tool_with_mock_pipeline(self, context: str = "ctx", chunks: int = 2) -> RetrievalTool:
        from app.services.vector_service import VectorService
        from app.retrieval.retrieval_pipeline import RetrievalPipeline
        from app.models.retrieval_result import RetrievalResult as RR

        mock_vs = MagicMock(spec=VectorService)
        tool = RetrievalTool(vector_service=mock_vs)

        # Patch the pipeline run
        mock_result = MagicMock(spec=RR)
        mock_result.context = context
        mock_result.citations = [Citation(document="a.pdf", chunk_id="c1", score=0.9)]
        mock_result.chunks_found = chunks

        import app.tools.retrieval_tool as rt_mod
        original = rt_mod.RetrievalPipeline

        class _FakePipeline:
            def __init__(self, service=None): pass
            async def run(self, query, cfg=None): return mock_result

        rt_mod.RetrievalPipeline = _FakePipeline
        self._restore = lambda: setattr(rt_mod, "RetrievalPipeline", original)
        return tool

    def test_returns_retrieval_result(self) -> None:
        tool = self._make_tool_with_mock_pipeline("20 days of leave.")
        result = asyncio.get_event_loop().run_until_complete(tool.run("leave days"))
        self._restore()
        assert isinstance(result, RetrievalResult)
        assert result.context == "20 days of leave."

    def test_chunks_found_propagated(self) -> None:
        tool = self._make_tool_with_mock_pipeline(chunks=3)
        result = asyncio.get_event_loop().run_until_complete(tool.run("leave?"))
        self._restore()
        assert result.chunks_found == 3

    def test_citations_list(self) -> None:
        tool = self._make_tool_with_mock_pipeline()
        result = asyncio.get_event_loop().run_until_complete(tool.run("leave?"))
        self._restore()
        assert isinstance(result.citations, list)
