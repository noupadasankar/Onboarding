"""Tests for VectorService."""
import pytest

from app.repositories.vector_repository import VectorRepository
from app.services.vector_service import VectorService
from tests.vectorstore.conftest import (
    DOC_ID,
    DOC_ID_2,
    make_embedded_batch,
)


class TestIndex:
    def test_index_returns_count(self, vector_service: VectorService) -> None:
        ecs, texts = make_embedded_batch(3)
        assert vector_service.index(ecs, texts) == 3

    def test_index_empty_returns_zero(self, vector_service: VectorService) -> None:
        assert vector_service.index([], {}) == 0

    def test_is_indexed_true_after_index(self, vector_service: VectorService) -> None:
        ecs, texts = make_embedded_batch(2)
        vector_service.index(ecs, texts)
        assert vector_service.is_indexed(DOC_ID) is True

    def test_is_indexed_false_before_index(self, vector_service: VectorService) -> None:
        assert vector_service.is_indexed("nonexistent") is False

    def test_upsert_does_not_duplicate(self, vector_service: VectorService) -> None:
        ecs, texts = make_embedded_batch(3)
        vector_service.index(ecs, texts)
        vector_service.index(ecs, texts)
        assert vector_service.total_chunks() == 3


class TestReindex:
    def test_reindex_replaces_existing(self, vector_service: VectorService) -> None:
        ecs, texts = make_embedded_batch(3)
        vector_service.index(ecs, texts)
        # Reindex with fresh set
        ecs2, texts2 = make_embedded_batch(2)
        vector_service.reindex_document(DOC_ID, ecs2, texts2)
        assert vector_service.total_chunks() == 2


class TestDelete:
    def test_delete_document_removes_all_chunks(self, vector_service: VectorService) -> None:
        ecs, texts = make_embedded_batch(4)
        vector_service.index(ecs, texts)
        deleted = vector_service.delete_document(DOC_ID)
        assert deleted == 4
        assert vector_service.total_chunks() == 0

    def test_delete_document_leaves_other_documents(self, vector_service: VectorService) -> None:
        ecs1, texts1 = make_embedded_batch(3, doc_id=DOC_ID)
        ecs2, texts2 = make_embedded_batch(2, doc_id=DOC_ID_2)
        vector_service.index(ecs1, texts1)
        vector_service.index(ecs2, texts2)
        vector_service.delete_document(DOC_ID)
        assert vector_service.total_chunks() == 2

    def test_delete_chunk(self, vector_service: VectorService) -> None:
        ecs, texts = make_embedded_batch(2)
        vector_service.index(ecs, texts)
        result = vector_service.delete_chunk(ecs[0].chunk_id)
        assert result is True
        assert vector_service.total_chunks() == 1

    def test_delete_unknown_chunk_returns_false(self, vector_service: VectorService) -> None:
        assert vector_service.delete_chunk("nonexistent_chunk") is False


class TestStats:
    def test_health_true(self, vector_service: VectorService) -> None:
        assert vector_service.health() is True

    def test_total_chunks_accurate(self, vector_service: VectorService) -> None:
        ecs, texts = make_embedded_batch(6)
        vector_service.index(ecs, texts)
        assert vector_service.total_chunks() == 6

    def test_unique_document_count(self, vector_service: VectorService) -> None:
        ecs1, texts1 = make_embedded_batch(3, doc_id=DOC_ID)
        ecs2, texts2 = make_embedded_batch(3, doc_id=DOC_ID_2)
        vector_service.index(ecs1, texts1)
        vector_service.index(ecs2, texts2)
        assert vector_service.unique_document_count() == 2

    def test_stats_returns_collection_stats(self, vector_service: VectorService) -> None:
        ecs, texts = make_embedded_batch(3)
        vector_service.index(ecs, texts)
        st = vector_service.stats()
        assert st.total_chunks == 3
        assert st.collection_name == "test_collection"


class TestSearch:
    def test_search_returns_results(self, vector_service: VectorService) -> None:
        ecs, texts = make_embedded_batch(5)
        vector_service.index(ecs, texts)
        results = vector_service.search(ecs[0].embedding, n_results=3)
        assert len(results) >= 1

    def test_search_top_result_is_self(self, vector_service: VectorService) -> None:
        ecs, texts = make_embedded_batch(5)
        vector_service.index(ecs, texts)
        results = vector_service.search(ecs[0].embedding, n_results=5)
        assert results[0].chunk_id == ecs[0].chunk_id

    def test_search_filtered_by_department(self, vector_service: VectorService) -> None:
        ecs, texts = make_embedded_batch(3)
        vector_service.index(ecs, texts)
        results = vector_service.search(ecs[0].embedding, n_results=5, department="HR")
        assert len(results) >= 1
