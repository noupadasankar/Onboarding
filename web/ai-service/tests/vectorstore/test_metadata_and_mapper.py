"""Tests for metadata_builder and vector_mapper."""
import pytest

from app.models.embedded_chunk import EmbeddedChunk
from app.vectorstore.metadata_builder import _to_scalar, build_chroma_metadata
from app.vectorstore.vector_mapper import (
    batch_to_upsert_args,
    chroma_query_to_search_results,
    chroma_result_to_vector_documents,
    embedded_chunk_to_upsert_args,
)


def _make_ec(chunk_id: str = "aaaabbbb_chunk0000", doc_id: str = "doc-001") -> EmbeddedChunk:
    return EmbeddedChunk(
        chunk_id=chunk_id,
        document_id=doc_id,
        embedding=[0.1, -0.2, 0.3],
        dimensions=3,
        provider="local",
        model="local-hash-v1",
        token_count=42,
        metadata={
            "filename": "handbook.txt",
            "file_type": "txt",
            "department": "HR",
            "category": "policy",
            "section": "Leave Policy",
            "page": 3,
            "source": "test/handbook.txt",
            "uploaded_by": "u_test",
        },
    )


class TestBuildChromaMetadata:
    def test_chunk_id_present(self) -> None:
        ec = _make_ec()
        m = build_chroma_metadata(ec)
        assert m["chunk_id"] == ec.chunk_id

    def test_document_id_present(self) -> None:
        ec = _make_ec()
        m = build_chroma_metadata(ec)
        assert m["document_id"] == ec.document_id

    def test_department_present(self) -> None:
        ec = _make_ec()
        m = build_chroma_metadata(ec)
        assert m["department"] == "HR"

    def test_section_present(self) -> None:
        ec = _make_ec()
        m = build_chroma_metadata(ec)
        assert m["section"] == "Leave Policy"

    def test_page_is_int(self) -> None:
        ec = _make_ec()
        m = build_chroma_metadata(ec)
        assert isinstance(m["page"], int)
        assert m["page"] == 3

    def test_page_none_becomes_minus_one(self) -> None:
        ec = _make_ec()
        ec.metadata.pop("page", None)
        m = build_chroma_metadata(ec)
        assert m["page"] == -1

    def test_all_values_are_scalars(self) -> None:
        ec = _make_ec()
        m = build_chroma_metadata(ec)
        for k, v in m.items():
            assert isinstance(v, (str, int, float, bool)), (
                f"Key {k!r} has non-scalar type {type(v)}"
            )

    def test_indexed_at_overridden(self) -> None:
        ec = _make_ec()
        m = build_chroma_metadata(ec, indexed_at="2026-01-01T00:00:00+00:00")
        assert m["indexed_at"] == "2026-01-01T00:00:00+00:00"

    def test_nested_value_serialised_to_string(self) -> None:
        ec = _make_ec()
        ec.metadata["nested"] = {"key": "value"}
        m = build_chroma_metadata(ec)
        assert isinstance(m.get("nested"), str)


class TestToScalar:
    def test_none_becomes_empty_string(self) -> None:
        assert _to_scalar(None) == ""

    def test_string_unchanged(self) -> None:
        assert _to_scalar("hello") == "hello"

    def test_int_unchanged(self) -> None:
        assert _to_scalar(42) == 42

    def test_float_unchanged(self) -> None:
        assert _to_scalar(3.14) == 3.14

    def test_bool_unchanged(self) -> None:
        assert _to_scalar(True) is True

    def test_list_serialised(self) -> None:
        result = _to_scalar([1, 2, 3])
        assert isinstance(result, str)

    def test_dict_serialised(self) -> None:
        result = _to_scalar({"a": 1})
        assert isinstance(result, str)


class TestVectorMapper:
    def test_single_upsert_args_structure(self) -> None:
        ec = _make_ec()
        args = embedded_chunk_to_upsert_args(ec, "chunk text here")
        assert len(args["ids"]) == 1
        assert len(args["embeddings"]) == 1
        assert len(args["documents"]) == 1
        assert len(args["metadatas"]) == 1
        assert args["ids"][0] == ec.chunk_id

    def test_batch_upsert_args_length(self) -> None:
        items = [(_make_ec(f"aaaabbbb_chunk{i:04d}"), f"text {i}") for i in range(5)]
        args = batch_to_upsert_args(items)
        assert len(args["ids"]) == 5
        assert len(args["embeddings"]) == 5
        assert len(args["documents"]) == 5

    def test_chroma_result_to_vector_documents(self) -> None:
        result = {
            "ids": ["chunk0001"],
            "embeddings": [[0.1, 0.2]],
            "documents": ["some text"],
            "metadatas": [{"document_id": "doc-1", "filename": "f.txt"}],
        }
        docs = chroma_result_to_vector_documents(result)
        assert len(docs) == 1
        assert docs[0].chunk_id == "chunk0001"
        assert docs[0].document_id == "doc-1"
        assert docs[0].text == "some text"

    def test_chroma_query_to_search_results(self) -> None:
        query_result = {
            "ids": [["chunk0001", "chunk0002"]],
            "documents": [["text one", "text two"]],
            "metadatas": [[{"document_id": "doc-1"}, {"document_id": "doc-2"}]],
            "distances": [[0.1, 0.4]],
        }
        results = chroma_query_to_search_results(query_result)
        assert len(results) == 2
        # Lower distance → higher score
        assert results[0].score > results[1].score

    def test_search_result_score_range(self) -> None:
        query_result = {
            "ids": [["c1"]],
            "documents": [["text"]],
            "metadatas": [[{"document_id": "d1"}]],
            "distances": [[0.0]],   # identical
        }
        results = chroma_query_to_search_results(query_result)
        assert results[0].score == 1.0
