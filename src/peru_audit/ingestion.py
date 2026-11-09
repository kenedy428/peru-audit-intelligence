import hashlib
import json
import logging
import time
from datetime import UTC
from importlib.metadata import version
from pathlib import Path
from tempfile import NamedTemporaryFile

import httpx
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from peru_audit.config import Settings
from peru_audit.database import Chunk, Document, Page, ProcessingRun, now
from peru_audit.documents import chunk_pages, extract_pdf
from peru_audit.schemas import ManifestEntry, official_url

logger = logging.getLogger(__name__)


def read_manifest(path: Path) -> list[ManifestEntry]:
    entries = TypeAdapter(list[ManifestEntry]).validate_json(path.read_text(encoding="utf-8"))
    if not entries:
        raise ValueError("El manifiesto está vacío")
    if any(not entry.reviewed for entry in entries):
        raise ValueError("Todos los documentos deben estar revisados antes de descargarlos")
    return entries


def _download_pdf_once(
    url: str, settings: Settings, client: httpx.Client, expected_hash: str | None = None
) -> tuple[Path, str]:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        for _ in range(4):
            official_url(url)
            with client.stream("GET", url, follow_redirects=False) as response:
                if response.is_redirect:
                    url = str(response.url.join(response.headers["location"]))
                    continue
                response.raise_for_status()
                mime = response.headers.get("content-type", "").split(";")[0].strip().lower()
                if mime not in ("application/pdf", "application/octet-stream"):
                    raise ValueError("La fuente no devolvió un PDF")
                digest = hashlib.sha256()
                size = 0
                with NamedTemporaryFile(dir=settings.data_dir, suffix=".part", delete=False) as out:
                    temporary = Path(out.name)
                    for block in response.iter_bytes(65536):
                        size += len(block)
                        if size > settings.max_pdf_bytes:
                            raise ValueError("PDF supera el límite de descarga")
                        digest.update(block)
                        out.write(block)
                with temporary.open("rb") as stream:
                    if not stream.read(1024).lstrip().startswith(b"%PDF-"):
                        raise ValueError("Firma PDF inválida")
                checksum = digest.hexdigest()
                if expected_hash and checksum != expected_hash:
                    raise ValueError("El PDF no coincide con el SHA-256 esperado")
                destination = settings.data_dir / f"{checksum}.pdf"
                temporary.replace(destination)
                return destination, checksum
        raise ValueError("Demasiadas redirecciones en la descarga")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def download_pdf(
    url: str,
    settings: Settings,
    client: httpx.Client,
    expected_hash: str | None = None,
    use_cache: bool = False,
) -> tuple[Path, str]:
    official_url(url)
    if expected_hash is not None:
        import re

        if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError("SHA-256 esperado inválido")
        cached = settings.data_dir / f"{expected_hash}.pdf"
        if use_cache and cached.is_file():
            if cached.stat().st_size > settings.max_pdf_bytes:
                raise ValueError("PDF en caché supera el límite de tamaño")
            with cached.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != expected_hash:
                    raise ValueError("La caché no coincide con el SHA-256 esperado")
            return cached, expected_hash
    for attempt in range(3):
        try:
            return _download_pdf_once(url, settings, client, expected_hash)
        except httpx.HTTPStatusError as error:
            if error.response.status_code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except httpx.TransportError:
            if attempt == 2:
                raise
        time.sleep(attempt + 1)
    raise RuntimeError("Descarga no completada")


def ingest_entry(
    session: Session,
    entry: ManifestEntry,
    settings: Settings,
    client: httpx.Client,
    create_chunks: bool = True,
    use_cache: bool = False,
) -> tuple[str, str]:
    if not entry.reviewed:
        raise ValueError("Documento pendiente de revisión")
    run = ProcessingRun(source_url=entry.source_url)
    session.add(run)
    session.commit()
    run_id = run.run_id
    try:
        using_cache = bool(
            use_cache
            and entry.expected_sha256
            and (settings.data_dir / f"{entry.expected_sha256}.pdf").is_file()
        )
        if using_cache and entry.cached_downloaded_at is None:
            raise ValueError("La caché requiere su fecha original de descarga")
        path, checksum = download_pdf(
            entry.source_url, settings, client, entry.expected_sha256, use_cache
        )
        existing = session.scalar(select(Document).where(Document.source_hash == checksum))
        if existing is not None:
            run.status = "duplicate"
            run.document_id = existing.document_id
            run.finished_at = now()
            session.commit()
            return existing.document_id, "duplicate"
        document = Document(
            **entry.model_dump(exclude={"reviewed", "expected_sha256", "cached_downloaded_at"}),
            source_hash=checksum,
            local_path=str(path),
            downloaded_at=entry.cached_downloaded_at.astimezone(UTC) if using_cache else now(),
            pipeline_version="page-extraction-v2" if not create_chunks else "page-words-v2",
            processing_config={
                "create_chunks": create_chunks,
                "download_source": "verified_cache" if using_cache else "https",
                "extractor_version": f"pypdf:{version('pypdf')}",
                "chunk_words": settings.chunk_words,
                "overlap_words": settings.chunk_overlap_words,
                "page_numbering": "physical_1_based",
            },
        )
        session.add(document)
        session.flush()
        pages = extract_pdf(path, settings.max_pdf_pages)
        document.processing_config = {
            **document.processing_config,
            "extraction_errors": {
                str(page.number): page.extraction_error for page in pages if page.extraction_error
            },
        }
        for page in pages:
            session.add(
                Page(
                    document_id=document.document_id,
                    page_number=page.number,
                    original_text=page.original_text,
                    page_text=page.text,
                    has_text=bool(page.text),
                )
            )
        chunks = (
            chunk_pages(pages, settings.chunk_words, settings.chunk_overlap_words)
            if create_chunks
            else []
        )
        for index, chunk in enumerate(chunks):
            session.add(
                Chunk(
                    document_id=document.document_id,
                    page_start=chunk.page_number,
                    page_end=chunk.page_number,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    chunk_index=index,
                    chunk_text=chunk.text,
                    word_count=chunk.word_count,
                )
            )
        document.processing_status = (
            "ready"
            if all(page.text for page in pages)
            else "partial_text"
            if any(page.text for page in pages)
            else "needs_ocr"
        )
        run.document_id = document.document_id
        run.status = "completed"
        run.finished_at = now()
        session.commit()
        logger.info(
            json.dumps(
                {"run_id": run_id, "status": "completed", "document_id": document.document_id}
            )
        )
        return document.document_id, document.processing_status
    except Exception as error:
        session.rollback()
        run = session.get(ProcessingRun, run_id)
        run.status = "failed"
        # Persist error categories, not raw URLs, credentials or response bodies.
        run.error = type(error).__name__
        run.finished_at = now()
        session.commit()
        logger.error(json.dumps({"run_id": run_id, "status": "failed", "error": run.error}))
        raise
