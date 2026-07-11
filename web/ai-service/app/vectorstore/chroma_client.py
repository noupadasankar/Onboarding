"""ChromaDB client — singleton connection manager.

Wraps chromadb to provide:
  * A single shared client instance (never create one per request).
  * Mode selection: "http" (remote server) vs "memory" (ephemeral, for tests).
  * Health check.
  * Graceful teardown.

Usage::

    from app.vectorstore.chroma_client import get_chroma_client
    client = get_chroma_client()          # returns the singleton
    collection = client.get_or_create("hr_documents")
"""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    import chromadb as _chromadb_t

_log = get_logger()
_lock = threading.Lock()
_instance: "ChromaClient | None" = None


class ChromaClientError(RuntimeError):
    """Raised when the Chroma client cannot connect or is unavailable."""


class ChromaClient:
    """Thin wrapper around the chromadb client.

    Args:
        mode: ``"http"`` uses ``chromadb.HttpClient``; ``"memory"`` uses
              ``chromadb.EphemeralClient`` (no server required — ideal for tests).
        url: Chroma server URL (only used in ``"http"`` mode).
        tenant: Chroma tenant name.
        database: Chroma database name.
    """

    def __init__(
        self,
        mode: str = "http",
        url: str = "http://localhost:8200",
        tenant: str = "default_tenant",
        database: str = "default_database",
    ) -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise ImportError(
                "chromadb package is required. Install with: pip install 'chromadb>=0.5,<1'"
            ) from exc

        self._mode = mode
        if mode == "memory":
            self._client = chromadb.EphemeralClient()
            _log.info("chroma_client_memory", mode="memory")
        else:
            self._client = chromadb.HttpClient(
                host=url.replace("http://", "").replace("https://", "").split(":")[0],
                port=int(url.rsplit(":", 1)[-1]) if ":" in url.split("//")[-1] else 8200,
                tenant=tenant,
                database=database,
            )
            _log.info("chroma_client_http", url=url, tenant=tenant, database=database)

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def raw(self) -> "_chromadb_t.ClientAPI":
        """Return the underlying chromadb client."""
        return self._client

    def heartbeat(self) -> bool:
        """Return True if Chroma responds to a heartbeat ping."""
        try:
            self._client.heartbeat()
            return True
        except Exception:
            return False

    def get_or_create_collection(
        self,
        name: str,
        metadata: dict | None = None,
    ) -> "_chromadb_t.Collection":
        """Return an existing collection or create it if it doesn't exist.

        Args:
            name: Collection name (e.g. ``hr_documents``).
            metadata: Optional creation metadata (e.g. HNSW settings).
        """
        return self._client.get_or_create_collection(
            name=name,
            metadata=metadata or {"hnsw:space": "cosine"},
        )

    def delete_collection(self, name: str) -> None:
        """Delete a collection and all its data."""
        try:
            self._client.delete_collection(name=name)
            _log.info("chroma_collection_deleted", name=name)
        except Exception as exc:
            _log.warning("chroma_collection_delete_failed", name=name, error=str(exc))

    def list_collections(self) -> list[str]:
        """Return names of all existing collections."""
        try:
            return [c.name for c in self._client.list_collections()]
        except Exception:
            return []


# ── Module-level singleton ─────────────────────────────────────────────────────

def get_chroma_client() -> ChromaClient:
    """Return (or lazily create) the process-wide ChromaClient singleton.

    Reads ``chroma_mode``, ``chroma_url``, ``chroma_tenant``, ``chroma_database``
    from settings.
    """
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                from app.core.config import get_settings
                s = get_settings()
                _instance = ChromaClient(
                    mode=s.chroma_mode,
                    url=s.chroma_url,
                    tenant=s.chroma_tenant,
                    database=s.chroma_database,
                )
    return _instance


def reset_chroma_client() -> None:
    """Reset the singleton — used in tests to inject a fresh memory client."""
    global _instance
    with _lock:
        _instance = None
