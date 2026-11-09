import httpx
import pytest
from sqlalchemy import func, select

from peru_audit.chunking import chunk_document
from peru_audit.database import Chunk, Document, Page, ProcessingRun
from peru_audit.ingestion import ingest_entry
from peru_audit.retrieval import search
from peru_audit.schemas import ManifestEntry, SearchRequest
from tests.conftest import pdf_bytes


def extracted(session, settings, texts=("Synthetic backup evidence " * 100, "")):
    entry = ManifestEntry(
        report_number="CHUNK-TEST",
        title="Synthetic",
        entity_name="Synthetic",
        control_type="Test",
        reviewed=True,
        source_url="https://apps8.contraloria.gob.pe/synthetic.pdf",
    )
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=pdf_bytes(texts), headers={"content-type": "application/pdf"}
            )
        )
    ) as client:
        return ingest_entry(session, entry, settings, client, create_chunks=False)[0]


def test_extract_chunk_search_preserves_sources_and_is_idempotent(session, settings):
    doc_id = extracted(session, settings)
    doc = session.get(Document, doc_id)
    provenance = (doc.source_hash, doc.source_url, doc.downloaded_at, doc.processing_status)
    original = [
        (p.page_number, p.original_text, p.page_text) for p in session.scalars(select(Page))
    ]
    result = chunk_document(session, doc_id, settings)
    assert result["status"] == "chunk_completed"
    chunks = list(session.scalars(select(Chunk).order_by(Chunk.chunk_index)))
    identifiers = [c.chunk_id for c in chunks]
    assert len(chunks) > 1
    for chunk in chunks:
        page = session.scalar(
            select(Page).where(Page.document_id == doc_id, Page.page_number == chunk.page_start)
        )
        assert page.page_text[chunk.char_start : chunk.char_end] == chunk.chunk_text
        assert chunk.page_start == chunk.page_end == 1
        assert chunk.embedding is None
    assert search(session, SearchRequest(query="backup"))[0].source_hash == doc.source_hash
    assert chunk_document(session, doc_id, settings)["status"] == "chunk_unchanged"
    assert [
        c.chunk_id for c in session.scalars(select(Chunk).order_by(Chunk.chunk_index))
    ] == identifiers
    assert (doc.source_hash, doc.source_url, doc.downloaded_at, doc.processing_status) == provenance
    assert [
        (p.page_number, p.original_text, p.page_text) for p in session.scalars(select(Page))
    ] == original
    assert doc.processing_config["extractor_version"].startswith("pypdf:")


def test_incompatible_configuration_is_rejected_without_overwriting(session, settings):
    doc_id = extracted(session, settings)
    chunk_document(session, doc_id, settings)
    before = session.scalar(select(func.count()).select_from(Chunk))
    changed = settings.model_copy(update={"chunk_words": 200})
    with pytest.raises(ValueError, match="incompatible"):
        chunk_document(session, doc_id, changed)
    assert session.scalar(select(func.count()).select_from(Chunk)) == before
    assert (
        session.scalars(select(ProcessingRun).where(ProcessingRun.status == "chunk_failed"))
        .one()
        .error
        == "ValueError"
    )


def test_missing_or_unextractable_document(session, settings):
    with pytest.raises(ValueError, match="no encontrado"):
        chunk_document(session, "missing", settings)
    doc_id = extracted(session, settings, ("",))
    with pytest.raises(ValueError, match="No hay texto"):
        chunk_document(session, doc_id, settings)
    assert session.scalar(select(func.count()).select_from(Chunk)) == 0


def test_chunk_failure_is_atomic(session, settings, monkeypatch):
    doc_id = extracted(session, settings)
    original_flush = session.flush

    def fail_chunks(*args, **kwargs):
        if any(isinstance(item, Chunk) for item in session.new):
            raise RuntimeError("Synthetic storage failure")
        return original_flush(*args, **kwargs)

    monkeypatch.setattr(session, "flush", fail_chunks)
    with pytest.raises(RuntimeError):
        chunk_document(session, doc_id, settings)
    assert session.scalar(select(func.count()).select_from(Chunk)) == 0
    assert session.get(Document, doc_id).processing_config["create_chunks"] is False
