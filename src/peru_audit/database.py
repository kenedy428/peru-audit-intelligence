from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    create_engine,
    event,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


def uid() -> str:
    return str(uuid4())


def now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    report_number: Mapped[str] = mapped_column(String(150), index=True)
    title: Mapped[str]
    entity_name: Mapped[str] = mapped_column(index=True)
    control_type: Mapped[str]
    issue_date: Mapped[date | None]
    publication_date: Mapped[date | None]
    region: Mapped[str | None]
    auditor: Mapped[str | None]
    document_kind: Mapped[str]
    source_url: Mapped[str]
    source_hash: Mapped[str] = mapped_column(String(64), unique=True)
    local_path: Mapped[str]
    downloaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    processing_status: Mapped[str] = mapped_column(default="registered")
    pipeline_version: Mapped[str] = mapped_column(default="page-words-v1")
    processing_config: Mapped[dict] = mapped_column(JSON, default=dict)


class Page(Base):
    __tablename__ = "pages"
    __table_args__ = (UniqueConstraint("document_id", "page_number"),)

    page_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.document_id"), index=True)
    page_number: Mapped[int]
    original_text: Mapped[str]
    page_text: Mapped[str]
    has_text: Mapped[bool]


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index"),)

    chunk_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.document_id"), index=True)
    page_start: Mapped[int]
    page_end: Mapped[int]
    char_start: Mapped[int]
    char_end: Mapped[int]
    chunk_index: Mapped[int]
    chunk_text: Mapped[str]
    word_count: Mapped[int]
    # Dimension-free storage permits versioned models; exact search for the small MVP.
    embedding: Mapped[list | None] = mapped_column(
        Vector().with_variant(JSON(none_as_null=True), "sqlite")
    )
    embedding_fingerprint: Mapped[str | None]
    embedded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProcessingRun(Base):
    __tablename__ = "processing_runs"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str]
    document_id: Mapped[str | None]
    status: Mapped[str] = mapped_column(default="running")
    error: Mapped[str | None]


class Database:
    def __init__(self, url: str):
        if url.startswith("sqlite:///") and ":memory:" not in url:
            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(url, **kwargs)
        if self.engine.dialect.name == "sqlite":
            event.listen(self.engine, "connect", self._sqlite_foreign_keys)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    @staticmethod
    def _sqlite_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    def initialize(self):
        if self.engine.dialect.name == "postgresql":
            with self.engine.begin() as connection:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(self.engine)

    def session(self) -> Iterator[Session]:
        with self.sessions() as session:
            yield session
