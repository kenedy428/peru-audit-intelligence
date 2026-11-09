"""Create searchable fragments from preserved pages, without downloading or extracting again."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from peru_audit.config import Settings
from peru_audit.database import Chunk, Document, Page, ProcessingRun, now
from peru_audit.documents import ExtractedPage, chunk_pages


def chunk_document(session: Session, document_id: str, settings: Settings) -> dict:
    document = session.get(Document, document_id)
    if document is None:
        raise ValueError("Informe no encontrado")
    run = ProcessingRun(source_url=document.source_url, document_id=document_id)
    session.add(run)
    session.commit()
    run_id = run.run_id
    try:
        document = session.scalar(
            select(Document).where(Document.document_id == document_id).with_for_update()
        )
        config = document.processing_config
        existing = list(session.scalars(select(Chunk).where(Chunk.document_id == document_id)))
        if existing:
            if (
                document.pipeline_version not in ("page-words-v1", "page-words-v2")
                or config.get("chunk_words") != settings.chunk_words
                or config.get("overlap_words") != settings.chunk_overlap_words
            ):
                raise ValueError("Ya hay fragmentos con configuración incompatible; usa otra base")
            status, count = "chunk_unchanged", len(existing)
        else:
            pages = list(
                session.scalars(
                    select(Page).where(Page.document_id == document_id).order_by(Page.page_number)
                )
            )
            fragments = chunk_pages(
                [ExtractedPage(p.page_number, p.original_text, p.page_text) for p in pages],
                settings.chunk_words,
                settings.chunk_overlap_words,
            )
            if not fragments:
                raise ValueError("No hay texto extraíble para crear fragmentos; revisa la calidad")
            for index, fragment in enumerate(fragments):
                session.add(
                    Chunk(
                        document_id=document_id,
                        chunk_index=index,
                        page_start=fragment.page_number,
                        page_end=fragment.page_number,
                        char_start=fragment.char_start,
                        char_end=fragment.char_end,
                        chunk_text=fragment.text,
                        word_count=fragment.word_count,
                    )
                )
            document.pipeline_version = "page-words-v2"
            document.processing_config = {
                **config,
                "create_chunks": True,
                "chunk_words": settings.chunk_words,
                "overlap_words": settings.chunk_overlap_words,
            }
            status, count = "chunk_completed", len(fragments)
        run.status, run.finished_at = status, now()
        session.commit()
        return {"document_id": document_id, "status": status, "chunks": count}
    except Exception as error:
        session.rollback()
        run = session.get(ProcessingRun, run_id)
        run.status, run.error, run.finished_at = "chunk_failed", type(error).__name__, now()
        session.commit()
        raise
