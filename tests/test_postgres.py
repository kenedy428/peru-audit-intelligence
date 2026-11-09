import os
from datetime import date

import pytest

from peru_audit.database import Chunk, Database, Document
from peru_audit.retrieval import index_chunks, search
from peru_audit.schemas import Filters, SearchRequest


@pytest.mark.postgres
def test_real_pgvector_exact_search_and_filters(embedder):
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL no configurado; PostgreSQL se verifica en CI")
    database = Database(url)
    database.initialize()
    try:
        with database.sessions() as session:
            document = Document(
                report_number="PG-SYNTHETIC",
                title="Synthetic pgvector fixture",
                entity_name="Synthetic PG entity",
                control_type="test",
                issue_date=date(2024, 1, 1),
                document_kind="report",
                source_url="https://apps8.contraloria.gob.pe/test.pdf",
                source_hash="p" * 64,
                local_path="fixture",
                processing_status="ready",
            )
            session.add(document)
            session.flush()
            for i, text in enumerate(["control de accesos", "respaldos digitales"]):
                session.add(
                    Chunk(
                        document_id=document.document_id,
                        page_start=i + 1,
                        page_end=i + 1,
                        char_start=0,
                        char_end=len(text),
                        chunk_index=i,
                        chunk_text=text,
                        word_count=3,
                    )
                )
            session.commit()
            assert index_chunks(session, embedder) == 2
            hits = search(
                session,
                SearchRequest(
                    query="accesos",
                    mode="semantic",
                    filters=Filters(document_ids=[document.document_id]),
                ),
                embedder,
            )
            assert hits[0].page_start == 1
            assert hits[0].score == pytest.approx(1)
            assert hits[1].score == pytest.approx(0)
            session.query(Chunk).filter_by(document_id=document.document_id).delete()
            session.delete(document)
            session.commit()
    finally:
        database.engine.dispose()
