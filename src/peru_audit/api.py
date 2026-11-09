import logging
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from peru_audit.config import Settings
from peru_audit.database import Chunk, Database, Document, Page
from peru_audit.providers import OllamaEmbeddings, OllamaGenerator, ProviderUnavailable
from peru_audit.rag import AskResponse, ask
from peru_audit.retrieval import filter_query, search
from peru_audit.schemas import AskRequest, Filters, SearchHit, SearchRequest, SimilarRequest

logger = logging.getLogger(__name__)


def document_dict(document: Document) -> dict:
    return {
        column.name: getattr(document, column.name)
        for column in Document.__table__.columns
        if column.name != "local_path"
    }


def create_app(settings: Settings | None = None, database: Database | None = None) -> FastAPI:
    settings = settings or Settings()
    database = database or Database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app):
        # Explicit init-db command owns schema creation; startup does not hide migrations.
        yield
        database.engine.dispose()

    app = FastAPI(title="Peru Audit Intelligence", version="0.1.0", lifespan=lifespan)
    session_dependency = Depends(database.session)

    @app.exception_handler(ProviderUnavailable)
    async def provider_error(_, error):
        return JSONResponse(status_code=503, content={"detail": str(error)})

    @app.exception_handler(SQLAlchemyError)
    async def database_error(_, error):
        logger.error("database_error", extra={"error_type": type(error).__name__})
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Base de datos no disponible. Ejecuta audit init-db y revisa la conexión."
            },
        )

    @app.get("/api/v1/health")
    def health(session: Session = session_dependency):
        session.execute(text("SELECT 1"))
        # Check schema as well as connectivity.
        session.scalar(select(func.count()).select_from(Document))
        return {
            "status": "ok",
            "database": database.engine.dialect.name,
            "generation_enabled": settings.generation_enabled,
        }

    @app.get("/api/v1/reports")
    def reports(
        entity: Annotated[str | None, Query(min_length=1, max_length=500)] = None,
        year: Annotated[int | None, Query(ge=1900, le=2100)] = None,
        region: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
        control_type: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
        report_number: str | None = None,
        title: str | None = None,
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        session: Session = session_dependency,
    ):
        statement = filter_query(
            select(Document),
            Filters(entity=entity, year=year, region=region, control_type=control_type),
        )
        if report_number:
            statement = statement.where(Document.report_number == report_number)
        if title:
            statement = statement.where(Document.title.icontains(title, autoescape=True))
        total = session.scalar(select(func.count()).select_from(statement.subquery()))
        rows = session.scalars(statement.order_by(Document.document_id).offset(offset).limit(limit))
        return {"total": total, "results": [document_dict(row) for row in rows]}

    def require_document(session, document_id):
        document = session.get(Document, document_id)
        if document is None:
            raise HTTPException(404, "Informe no encontrado")
        return document

    @app.get("/api/v1/reports/{document_id}")
    def report(document_id: str, session: Session = session_dependency):
        return document_dict(require_document(session, document_id))

    @app.get("/api/v1/reports/{document_id}/pages")
    def pages(
        document_id: str,
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        session: Session = session_dependency,
    ):
        require_document(session, document_id)
        rows = session.scalars(
            select(Page)
            .where(Page.document_id == document_id)
            .order_by(Page.page_number)
            .offset(offset)
            .limit(limit)
        )
        return {
            "results": [
                {
                    "page_number": row.page_number,
                    "text": row.page_text,
                    "original_text": row.original_text,
                    "has_text": row.has_text,
                }
                for row in rows
            ]
        }

    @app.post("/api/v1/search", response_model=dict[str, list[SearchHit]])
    def search_route(request: SearchRequest, session: Session = session_dependency):
        embedder = OllamaEmbeddings(settings) if request.mode == "semantic" else None
        return {"results": search(session, request, embedder)}

    @app.post("/api/v1/ask", response_model=AskResponse)
    def ask_route(request: AskRequest, session: Session = session_dependency):
        return ask(
            session, request, settings, OllamaEmbeddings(settings), OllamaGenerator(settings)
        )

    @app.post("/api/v1/similar", response_model=dict[str, list[SearchHit]])
    def similar(request: SimilarRequest, session: Session = session_dependency):
        chunk = session.get(Chunk, request.chunk_id)
        if chunk is None:
            raise HTTPException(404, "Fragmento no encontrado")
        return {
            "results": search(
                session,
                SearchRequest(
                    query="similar",
                    top_k=request.top_k,
                    filters=request.filters,
                    mode="semantic",
                ),
                OllamaEmbeddings(settings),
                exclude_chunk_id=chunk.chunk_id,
                query_text=chunk.chunk_text,
            )
        }

    @app.get("/api/v1/stats")
    def stats(session: Session = session_dependency):
        counts = {
            name: session.scalar(select(func.count()).select_from(model))
            for name, model in (("documents", Document), ("pages", Page), ("chunks", Chunk))
        }
        counts["indexed_chunks"] = session.scalar(
            select(func.count())
            .select_from(Chunk)
            .where(Chunk.embedding.is_not(None), Chunk.embedding_fingerprint.is_not(None))
        )
        counts["documents_with_chunks"] = session.scalar(
            select(func.count(func.distinct(Chunk.document_id)))
        )
        counts["entities"] = list(
            session.scalars(select(Document.entity_name).distinct().order_by(Document.entity_name))
        )
        counts["issue_years"] = sorted(
            {
                day.year
                for day in session.scalars(
                    select(Document.issue_date).where(Document.issue_date.is_not(None))
                )
            }
        )
        counts["generation_enabled"] = settings.generation_enabled
        return counts

    return app


def json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(type(value).__name__)
