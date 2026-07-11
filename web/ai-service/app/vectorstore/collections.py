"""Collection manager — named collection lifecycle on top of ChromaClient."""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.vectorstore.chroma_client import ChromaClient

if TYPE_CHECKING:
    import chromadb as _chromadb_t

_log = get_logger()


class CollectionManager:
    """Manages ChromaDB collection lifecycle for a single client.

    Args:
        client: The shared ChromaClient singleton.
    """

    def __init__(self, client: ChromaClient) -> None:
        self._client = client

    def get_or_create(
        self,
        name: str,
        hnsw_space: str = "cosine",
    ) -> "_chromadb_t.Collection":
        """Return (or create) a collection with HNSW cosine similarity.

        Args:
            name: Collection name.
            hnsw_space: Distance metric: ``"cosine"`` (default) or ``"l2"`` or ``"ip"``.
        """
        coll = self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": hnsw_space},
        )
        _log.info("collection_ready", name=name)
        return coll

    def delete(self, name: str) -> None:
        """Delete a collection and all its vectors."""
        self._client.delete_collection(name)

    def list_names(self) -> list[str]:
        """Return names of all existing collections."""
        return self._client.list_collections()
