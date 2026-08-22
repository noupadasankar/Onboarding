import asyncio
from pathlib import Path
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


async def _bootstrap_knowledge_base() -> None:
    """Bootstrap raw policy documents into the vector store on startup if empty."""
    log = get_logger()
    try:
        from app.services.vector_service import get_vector_service
        vs = get_vector_service()
        count = vs.total_chunks()
        if count > 0:
            log.info("knowledge_base_ready", total_chunks=count)
            return

        raw_dir = Path("data/raw")
        if not raw_dir.exists():
            # Try finding raw_dir relative to current working directory
            alt_path = Path("web/ai-service/data/raw")
            if alt_path.exists():
                raw_dir = alt_path
            else:
                log.warning("raw_data_dir_not_found", path=str(raw_dir))
                return

        from app.services.document_service import DocumentService
        from app.services.chunk_service import ChunkService, ChunkingConfig
        from app.rag.chunk_pipeline import ChunkPipeline
        from app.embeddings.embedding_pipeline import EmbeddingPipeline
        from app.embeddings.providers.local_provider import LocalProvider
        from app.embeddings.embedding_service import EmbeddingConfig

        doc_svc = DocumentService()
        chunk_svc = ChunkService()
        chunk_cfg = ChunkingConfig(chunk_size=800, overlap=100, min_tokens=40)
        chunk_pipeline = ChunkPipeline(chunk_svc, config=chunk_cfg)
        emb_pipeline = EmbeddingPipeline(provider=LocalProvider(), config=EmbeddingConfig())

        log.info("bootstrapping_knowledge_base_started", source_dir=str(raw_dir))
        total_indexed = 0

        # Prioritize key HR onboarding documents
        file_list = sorted(
            [p for p in raw_dir.glob("**/*.*") if p.is_file() and p.suffix.lower() in [".txt", ".csv", ".docx", ".xlsx", ".pdf"]],
            key=lambda p: 0 if "onboarding" in p.name.lower() or "faq" in p.name.lower() else 1
        )

        for file_path in file_list:
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                doc = await doc_svc.ingest(
                    content=content,
                    filename=file_path.name,
                    uploaded_by="system",
                    department=file_path.parent.name,
                )
                chunks = await chunk_pipeline.run(doc)
                if len(chunks) > 25:
                    chunks = chunks[:25]
                emb_chunks = await emb_pipeline.run(chunks)
                chunk_texts = {c.chunk_id: c.text for c in chunks}
                count = vs.index(emb_chunks, chunk_texts)
                total_indexed += count
                log.info("bootstrapped_document", file=file_path.name, chunks=count)
            except Exception as exc:
                log.warning("bootstrap_file_error", file=file_path.name, error=str(exc))

        final_count = vs.total_chunks()
        log.info("knowledge_base_bootstrap_complete", total_chunks=final_count)
    except Exception as exc:
        log.error("knowledge_base_bootstrap_failed", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger()

    log.info(
        "ai_service_startup",
        env=settings.app_env,
        port=settings.app_port,
        log_level=settings.log_level,
    )

    # Trigger background knowledge base bootstrap
    asyncio.create_task(_bootstrap_knowledge_base())

    yield

    log.info("ai_service_shutdown")
