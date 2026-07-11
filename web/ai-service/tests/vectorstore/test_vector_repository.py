"""Tests for VectorRepository (in-memory ChromaDB)."""
import pytest

from app.repositories.vector_repository import VectorRepository
from tests.vectorstore.conftest import (
    DOC_ID,
    DOC_ID_2,
    make_embedded,
    make_embedded_batch,
    make_chunk,
)


class TestUpsertBatch:
    def test_upsert_returns_count(self, repo: VectorRepository) -> None:
        ecs, texts = make_embedded_batch(3)
        assert repo.upsert_batch(list(zip(ecs, [texts[e.chunk_id] for e in ecs]))) == 3

    def test_upsert_empty_list_returns_zero(self, repo: VectorRepository) -> None:
        assert repo.upsert_batch([]) == 0

    def test_count_after_upsert(self, repo: VectorRepository) -> None:
        ecs, texts = make_embedded_batch(5)
        repo.upsert_batch([(e, texts[e.chunk_id]) for e in ecs])
        assert repo.count() == 5

    def test_upsert_idempotent_no_duplicates(self, repo: VectorRepository) -> None:
        ecs, texts = make_embedded_batch(3)
        items = [(e, texts[e.chunk_id]) for e in ecs]
        repo.upsert_batch(items)
        repo.upsert_batch(items)  # second upsert — same IDs
        assert repo.count() == 3  # not 6


class TestDeleteDocument:
    def test_delete_all_chunks_for_document(self, repo: VectorRepository) -> None:
        ecs, texts = make_embedded_batch(4)
        repo.upsert_batch([(e, texts[e.chunk_id]) for e in ecs])
        deleted = repo.delete_document(DOC_ID)
        assert deleted == 4
        assert repo.count() == 0

    def test_delete_unknown_document_returns_zero(self, repo: VectorRepository) -> None:
        assert repo.delete_document("nonexistent-id") == 0

    def test_delete_document_leaves_other_documents(self, repo: VectorRepository) -> None:
        ecs1, texts1 = make_embedded_batch(2, doc_id=DOC_ID)
        ecs2, texts2 = make_embedded_batch(3, doc_id=DOC_ID_2)
        all_items = [(e, texts1[e.chunk_id]) for e in ecs1] + [(e, texts2[e.chunk_id]) for e in ecs2]
        repo.upsert_batch(all_items)
        repo.delete_document(DOC_ID)
        assert repo.count() == 3


class TestDeleteChunk:
    def test_delete_existing_chunk_returns_true(self, repo: VectorRepository) -> None:
        chunk = make_chunk(0)
        ec, text = make_embedded(chunk)
        repo.upsert_batch([(ec, text)])
        assert repo.delete_chunk(ec.chunk_id) is True
        assert repo.count() == 0

    def test_delete_nonexistent_chunk_returns_false(self, repo: VectorRepository) -> None:
        assert repo.delete_chunk("does_not_exist") is False


class TestGetByDocument:
    def test_returns_all_chunks_for_document(self, repo: VectorRepository) -> None:
        ecs, texts = make_embedded_batch(4)
        repo.upsert_batch([(e, texts[e.chunk_id]) for e in ecs])
        docs = repo.get_by_document(DOC_ID)
        assert len(docs) == 4

    def test_returns_empty_for_unknown_document(self, repo: VectorRepository) -> None:
        assert repo.get_by_document("no-such-doc") == []

    def test_document_id_in_returned_records(self, repo: VectorRepository) -> None:
        ecs, texts = make_embedded_batch(2)
        repo.upsert_batch([(e, texts[e.chunk_id]) for e in ecs])
        docs = repo.get_by_document(DOC_ID)
        for d in docs:
            assert d.document_id == DOC_ID


class TestExists:
    def test_returns_true_after_upsert(self, repo: VectorRepository) -> None:
        chunk = make_chunk(0)
        ec, text = make_embedded(chunk)
        repo.upsert_batch([(ec, text)])
        assert repo.exists(ec.chunk_id) is True

    def test_returns_false_before_upsert(self, repo: VectorRepository) -> None:
        assert repo.exists("nonexistent_chunk_id") is False


class TestUniqueDocumentIds:
    def test_returns_all_unique_document_ids(self, repo: VectorRepository) -> None:
        ecs1, texts1 = make_embedded_batch(2, doc_id=DOC_ID)
        ecs2, texts2 = make_embedded_batch(2, doc_id=DOC_ID_2)
        all_items = [(e, texts1[e.chunk_id]) for e in ecs1] + [(e, texts2[e.chunk_id]) for e in ecs2]
        repo.upsert_batch(all_items)
        ids = repo.unique_document_ids()
        assert DOC_ID in ids
        assert DOC_ID_2 in ids
        assert len(ids) == 2


class TestSearch:
    def test_search_returns_results(self, repo: VectorRepository) -> None:
        ecs, texts = make_embedded_batch(5)
        repo.upsert_batch([(e, texts[e.chunk_id]) for e in ecs])
        query_vec = ecs[0].embedding
        results = repo.search(query_vec, n_results=3)
        assert len(results) <= 3
        assert len(results) >= 1

    def test_search_self_is_top_result(self, repo: VectorRepository) -> None:
        ecs, texts = make_embedded_batch(5)
        repo.upsert_batch([(e, texts[e.chunk_id]) for e in ecs])
        # Query with the exact same vector as ecs[0]
        results = repo.search(ecs[0].embedding, n_results=5)
        assert results[0].chunk_id == ecs[0].chunk_id

    def test_search_scores_descending(self, repo: VectorRepository) -> None:
        ecs, texts = make_embedded_batch(5)
        repo.upsert_batch([(e, texts[e.chunk_id]) for e in ecs])
        results = repo.search(ecs[0].embedding, n_results=5)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


class TestHealth:
    def test_health_true_with_valid_collection(self, repo: VectorRepository) -> None:
        assert repo.health() is True
