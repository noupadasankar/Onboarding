"""Tests for SearchFilters builder."""
from app.vectorstore.search_filters import SearchFilters


class TestSearchFilters:
    def test_no_filters_returns_none(self) -> None:
        assert SearchFilters().build() is None

    def test_single_filter(self) -> None:
        where = SearchFilters().by_department("HR").build()
        assert where == {"department": {"$eq": "HR"}}

    def test_multiple_filters_use_and(self) -> None:
        where = (
            SearchFilters()
            .by_department("HR")
            .by_section("Leave Policy")
            .build()
        )
        assert where is not None
        assert "$and" in where
        assert len(where["$and"]) == 2

    def test_by_document_filter(self) -> None:
        where = SearchFilters().by_document("doc-001").build()
        assert where == {"document_id": {"$eq": "doc-001"}}

    def test_by_filename_filter(self) -> None:
        where = SearchFilters().by_filename("handbook.txt").build()
        assert where == {"filename": {"$eq": "handbook.txt"}}

    def test_by_category_filter(self) -> None:
        where = SearchFilters().by_category("policy").build()
        assert where == {"category": {"$eq": "policy"}}

    def test_by_file_type_filter(self) -> None:
        where = SearchFilters().by_file_type("pdf").build()
        assert where == {"file_type": {"$eq": "pdf"}}

    def test_chaining_returns_self(self) -> None:
        sf = SearchFilters()
        result = sf.by_department("HR")
        assert result is sf
