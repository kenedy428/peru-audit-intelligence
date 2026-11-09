import os

import httpx
import pytest
from sqlalchemy import func, select

from peru_audit.chunking import chunk_document
from peru_audit.config import Settings
from peru_audit.database import Chunk, Database, Document, Page
from peru_audit.ingestion import ingest_entry
from peru_audit.quality import extraction_quality
from peru_audit.schemas import ManifestEntry
from tests.conftest import pdf_bytes


@pytest.mark.postgres
def test_real_postgres_extraction_only_and_quality(tmp_path):
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requires a disposable test database, never the project corpus")
    settings = Settings(_env_file=None, database_url=url, data_dir=tmp_path / "raw")
    database = Database(url)
    database.initialize()
    entry = ManifestEntry(
        report_number="PG-DOC-SYNTHETIC",
        title="Synthetic extraction fixture",
        entity_name="Synthetic test entity",
        control_type="Test only",
        reviewed=True,
        source_url="https://apps8.contraloria.gob.pe/synthetic-extraction.pdf",
    )
    body = pdf_bytes(("Synthetic PostgreSQL extraction evidence", ""))
    try:
        with database.sessions() as session:
            with httpx.Client(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(
                        200, content=body, headers={"content-type": "application/pdf"}
                    )
                )
            ) as client:
                doc_id, status = ingest_entry(session, entry, settings, client, create_chunks=False)
                repeated_id, repeated = ingest_entry(
                    session, entry, settings, client, create_chunks=False
                )
            assert status == "partial_text"
            assert repeated == "duplicate" and repeated_id == doc_id
            assert (
                session.scalar(
                    select(func.count()).select_from(Page).where(Page.document_id == doc_id)
                )
                == 2
            )
            assert (
                session.scalar(
                    select(func.count()).select_from(Chunk).where(Chunk.document_id == doc_id)
                )
                == 0
            )
            report = extraction_quality(session)
            result = next(doc for doc in report["documents"] if doc["document_id"] == doc_id)
            assert result["flags"]["no_text"] == 1
            assert result["pages"][1]["physical_page"] == 2
            assert result["source_url"] == entry.source_url
            assert chunk_document(session, doc_id, settings)["chunks"] == 1
            assert chunk_document(session, doc_id, settings)["status"] == "chunk_unchanged"
            session.query(Chunk).filter_by(document_id=doc_id).delete()
            session.query(Page).filter_by(document_id=doc_id).delete()
            session.delete(session.get(Document, doc_id))
            session.commit()
    finally:
        database.engine.dispose()
