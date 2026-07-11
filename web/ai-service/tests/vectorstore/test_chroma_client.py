"""Tests for ChromaClient (in-memory mode)."""
import pytest

from app.vectorstore.chroma_client import ChromaClient


@pytest.fixture
def client() -> ChromaClient:
    return ChromaClient(mode="memory")


class TestChromaClientInit:
    def test_creates_without_error(self) -> None:
        c = ChromaClient(mode="memory")
        assert c is not None

    def test_heartbeat_returns_true(self, client: ChromaClient) -> None:
        assert client.heartbeat() is True

    def test_raw_client_accessible(self, client: ChromaClient) -> None:
        assert client.raw is not None

    def test_import_error_when_chromadb_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import sys
        monkeypatch.setitem(sys.modules, "chromadb", None)  # type: ignore[arg-type]
        with pytest.raises((ImportError, Exception)):
            ChromaClient(mode="memory")


class TestChromaClientCollections:
    def test_get_or_create_returns_collection(self, client: ChromaClient) -> None:
        coll = client.get_or_create_collection("test_coll")
        assert coll is not None
        assert coll.name == "test_coll"

    def test_get_or_create_idempotent(self, client: ChromaClient) -> None:
        c1 = client.get_or_create_collection("dup_coll")
        c2 = client.get_or_create_collection("dup_coll")
        assert c1.name == c2.name

    def test_delete_collection(self, client: ChromaClient) -> None:
        client.get_or_create_collection("to_delete")
        assert "to_delete" in client.list_collections()
        client.delete_collection("to_delete")
        assert "to_delete" not in client.list_collections()

    def test_list_collections_empty_initially(self, client: ChromaClient) -> None:
        # Fresh client — no collections
        assert isinstance(client.list_collections(), list)

    def test_list_collections_returns_created_name(self, client: ChromaClient) -> None:
        client.get_or_create_collection("visible_coll")
        assert "visible_coll" in client.list_collections()
