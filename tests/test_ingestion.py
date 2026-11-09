import hashlib
import json
from datetime import UTC, datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import func, select

from peru_audit.database import Chunk, Document, Page, ProcessingRun
from peru_audit.documents import ExtractedPage
from peru_audit.ingestion import download_pdf, ingest_entry, read_manifest
from peru_audit.schemas import ManifestEntry, official_url
from tests.conftest import pdf_bytes

URL = "https://apps8.contraloria.gob.pe/synthetic.pdf"


def metadata(**overrides):
    return ManifestEntry(
        report_number="TEST-ONLY",
        title="Synthetic fixture",
        entity_name="Synthetic entity",
        control_type="Synthetic",
        source_url=URL,
        reviewed=True,
        **overrides,
    )


def test_ingestion_idempotent_with_traceability(session, settings):
    body = pdf_bytes(("Synthetic backup evidence", "Synthetic second page"))
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=body, headers={"content-type": "application/pdf"}
            )
        )
    ) as client:
        first, status = ingest_entry(session, metadata(), settings, client)
        second, duplicate = ingest_entry(session, metadata(), settings, client)
    assert (status, duplicate) == ("ready", "duplicate")
    assert first == second
    doc = session.get(Document, first)
    assert doc.source_hash == hashlib.sha256(body).hexdigest()
    assert session.scalar(select(func.count()).select_from(Document)) == 1
    assert session.scalar(select(func.count()).select_from(Page)) == 2
    assert session.scalar(select(func.count()).select_from(Chunk)) == 2
    assert session.scalar(select(func.count()).select_from(ProcessingRun)) == 2


@pytest.mark.parametrize(
    "url",
    [
        "http://apps8.contraloria.gob.pe/a",
        "https://example.com/a",
        "https://contraloria.gob.pe.evil.com/a",
        "https://user:pass@apps8.contraloria.gob.pe/a",
        "https://apps8.contraloria.gob.pe:444/a",
    ],
)
def test_reject_unofficial_sources(url):
    with pytest.raises(ValueError):
        official_url(url)


def test_redirect_must_stay_official(settings):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                302, headers={"location": "https://example.com/report.pdf"}
            )
        )
    ) as client:
        with pytest.raises(ValueError, match="oficial"):
            download_pdf(URL, settings, client)


def test_invalid_pdf_records_failure_without_partial_document(session, settings):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=b"HTML error", headers={"content-type": "application/pdf"}
            )
        )
    ) as client:
        with pytest.raises(ValueError, match="Firma"):
            ingest_entry(session, metadata(), settings, client)
    assert session.scalar(select(func.count()).select_from(Document)) == 0
    assert session.scalar(select(ProcessingRun)).status == "failed"
    assert not list(settings.data_dir.glob("*.part"))


def test_oversized_download_cleans_partial_file(settings):
    settings.max_pdf_bytes = 1024
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=b"%PDF-" + b"a" * 2000, headers={"content-type": "application/pdf"}
            )
        )
    ) as client:
        with pytest.raises(ValueError, match="límite"):
            download_pdf(URL, settings, client)
    assert not list(settings.data_dir.iterdir())


def test_manifest_requires_review(tmp_path):
    path = tmp_path / "manifest.json"
    entry = metadata().model_dump(mode="json")
    entry["reviewed"] = False
    path.write_text(json.dumps([entry]), encoding="utf-8")
    with pytest.raises(ValueError, match="revisados"):
        read_manifest(path)


def test_extract_only_has_no_chunks_and_is_idempotent(session, settings, monkeypatch):
    def disallow_chunking(*args):
        raise AssertionError("Extraction-only must never invoke chunking")

    monkeypatch.setattr("peru_audit.ingestion.chunk_pages", disallow_chunking)
    body = pdf_bytes(("Synthetic backup evidence", ""))
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=body, headers={"content-type": "application/pdf"}
            )
        )
    ) as client:
        doc_id, status = ingest_entry(session, metadata(), settings, client, create_chunks=False)
        duplicate_id, repeated = ingest_entry(
            session, metadata(), settings, client, create_chunks=False
        )
    assert status == "partial_text"
    assert repeated == "duplicate" and duplicate_id == doc_id
    assert session.scalar(select(func.count()).select_from(Page)) == 2
    assert session.scalar(select(func.count()).select_from(Chunk)) == 0
    assert session.get(Document, doc_id).processing_config["create_chunks"] is False


@pytest.mark.parametrize("offset", [UTC, timezone(timedelta(hours=-5))])
def test_verified_cache_preserves_download_date_without_network(session, settings, offset):
    body = pdf_bytes()
    digest = hashlib.sha256(body).hexdigest()
    settings.data_dir.mkdir(parents=True)
    (settings.data_dir / f"{digest}.pdf").write_bytes(body)
    original = datetime(2026, 1, 1, tzinfo=offset)
    entry = metadata(expected_sha256=digest, cached_downloaded_at=original)

    def disallow_network(request):
        raise AssertionError("Verified cache should not download")

    with httpx.Client(transport=httpx.MockTransport(disallow_network)) as client:
        doc_id, status = ingest_entry(
            session, entry, settings, client, create_chunks=False, use_cache=True
        )
    doc = session.get(Document, doc_id)
    assert status == "ready"
    # SQLite stores naive UTC; PostgreSQL preserves the timezone on the same column.
    assert doc.downloaded_at.replace(tzinfo=UTC) == original.astimezone(UTC)
    assert doc.processing_config["download_source"] == "verified_cache"
    assert doc.source_hash == digest and doc.source_url == URL


def test_corrupt_cache_is_not_accepted(settings):
    settings.data_dir.mkdir(parents=True)
    digest = "a" * 64
    (settings.data_dir / f"{digest}.pdf").write_bytes(b"corrupted")
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: pytest.fail("No network"))
    ) as client:
        with pytest.raises(ValueError, match="caché"):
            download_pdf(URL, settings, client, expected_hash=digest, use_cache=True)


def test_changed_official_pdf_does_not_overwrite_expected_hash(settings):
    body = pdf_bytes()
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=body, headers={"content-type": "application/pdf"}
            )
        )
    ) as client:
        with pytest.raises(ValueError, match="SHA-256 esperado"):
            download_pdf(URL, settings, client, expected_hash="a" * 64)
    assert not list(settings.data_dir.iterdir())


def test_transient_download_error_retries_only_bounded_attempts(settings, monkeypatch):
    monkeypatch.setattr("peru_audit.ingestion.time.sleep", lambda delay: None)
    calls = []

    def server(request):
        calls.append(request.url)
        return (
            httpx.Response(503)
            if len(calls) < 3
            else httpx.Response(
                200, content=pdf_bytes(), headers={"content-type": "application/pdf"}
            )
        )

    with httpx.Client(transport=httpx.MockTransport(server)) as client:
        path, digest = download_pdf(URL, settings, client)
    assert len(calls) == 3 and path.name == f"{digest}.pdf"


def test_authentication_error_is_not_retried(settings, monkeypatch):
    def disallow_sleep(delay):
        raise AssertionError("Authentication errors must not be retried")

    monkeypatch.setattr("peru_audit.ingestion.time.sleep", disallow_sleep)
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(403))) as client:
        with pytest.raises(httpx.HTTPStatusError):
            download_pdf(URL, settings, client)


def test_page_errors_remain_traceable_in_registry(session, settings, monkeypatch):
    monkeypatch.setattr(
        "peru_audit.ingestion.extract_pdf",
        lambda *args: [
            ExtractedPage(1, "Readable", "Readable"),
            ExtractedPage(2, "", "", "ValueError"),
        ],
    )
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=pdf_bytes(), headers={"content-type": "application/pdf"}
            )
        )
    ) as client:
        doc_id, status = ingest_entry(session, metadata(), settings, client, create_chunks=False)
    assert status == "partial_text"
    assert session.get(Document, doc_id).processing_config["extraction_errors"] == {
        "2": "ValueError"
    }
    assert [p.page_number for p in session.scalars(select(Page).order_by(Page.page_number))] == [
        1,
        2,
    ]
