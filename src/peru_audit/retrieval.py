import math
import re
import unicodedata
from collections.abc import Sequence

from sqlalchemy import extract, select
from sqlalchemy.orm import Session

from peru_audit.database import Chunk, Document, now
from peru_audit.providers import ProviderUnavailable, validate_vectors
from peru_audit.schemas import Filters, SearchHit, SearchRequest

STOPWORDS = frozenset(
    "de del la las el los un una unos unas y o en a al por para que qué "
    "se su sus con es son como cómo sobre informe informes".split()
)


def terms(text: str) -> set[str]:
    folded = "".join(
        c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn"
    )
    return {term for term in re.findall(r"\w+", folded) if len(term) > 1} - STOPWORDS


def filter_query(statement, filters: Filters):
    if filters.entity:
        statement = statement.where(Document.entity_name == filters.entity)
    if filters.year:
        # Explicitly use issue year, never silently substitute publication year.
        statement = statement.where(extract("year", Document.issue_date) == filters.year)
    if filters.region:
        statement = statement.where(Document.region == filters.region)
    if filters.control_type:
        statement = statement.where(Document.control_type == filters.control_type)
    if filters.document_ids:
        statement = statement.where(Document.document_id.in_(filters.document_ids))
    return statement


def hit(chunk: Chunk, doc: Document, score: float, mode: str) -> SearchHit:
    return SearchHit(
        chunk_id=chunk.chunk_id,
        document_id=doc.document_id,
        report_number=doc.report_number,
        title=doc.title,
        entity_name=doc.entity_name,
        document_kind=doc.document_kind,
        publication_date=doc.publication_date,
        issue_date=doc.issue_date,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        char_start=chunk.char_start,
        char_end=chunk.char_end,
        text=chunk.chunk_text,
        source_url=doc.source_url,
        source_hash=doc.source_hash,
        score=score,
        score_type="cosine_similarity" if mode == "semantic" else "keyword_coverage",
    )


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Dimensiones incompatibles")
    denominator = math.sqrt(sum(v * v for v in left) * sum(v * v for v in right))
    return sum(a * b for a, b in zip(left, right, strict=True)) / denominator if denominator else 0


def search(
    session: Session,
    request: SearchRequest,
    embedder=None,
    exclude_chunk_id: str | None = None,
    query_text: str | None = None,
) -> list[SearchHit]:
    query = query_text if query_text is not None else request.query
    statement = filter_query(select(Chunk, Document).join(Document), request.filters)
    if exclude_chunk_id:
        statement = statement.where(Chunk.chunk_id != exclude_chunk_id)
    if request.mode == "keyword":
        query_terms = terms(query)
        if not query_terms:
            return []
        scored = []
        for chunk, doc in session.execute(statement):
            score = len(query_terms & terms(chunk.chunk_text)) / len(query_terms)
            if score > 0:
                scored.append(hit(chunk, doc, score, "keyword"))
        return sorted(scored, key=ranking_key)[: request.top_k]
    if embedder is None:
        raise ProviderUnavailable("Configura el proveedor local de embeddings")
    fingerprint = embedder.fingerprint
    statement = statement.where(Chunk.embedding_fingerprint == fingerprint)
    # Avoid model inference for an empty or incompatible index.
    if session.execute(statement.limit(1)).first() is None:
        return []
    vector = validate_vectors(embedder.encode([query]), 1, embedder.dimension)[0]
    if session.bind.dialect.name == "postgresql":
        distance = Chunk.embedding.cosine_distance(vector)
        rows = session.execute(
            statement.add_columns(distance)
            .order_by(distance, Document.source_hash, Chunk.chunk_index)
            .limit(request.top_k)
        )
        return [hit(chunk, doc, float(1 - distance), "semantic") for chunk, doc, distance in rows]
    scored = [
        hit(chunk, doc, cosine(vector, chunk.embedding), "semantic")
        for chunk, doc in session.execute(statement)
    ]
    return sorted(scored, key=ranking_key)[: request.top_k]


def ranking_key(item: SearchHit):
    # Stable across databases and repeated ingestion; UUID ordering is not reproducible.
    return (-item.score, item.source_hash, item.page_start, item.char_start)


def index_chunks(session: Session, embedder, batch_size: int = 16) -> int:
    fingerprint = embedder.fingerprint
    chunks = session.scalars(
        select(Chunk)
        .where(
            (Chunk.embedding_fingerprint.is_(None)) | (Chunk.embedding_fingerprint != fingerprint)
        )
        .order_by(Chunk.document_id, Chunk.chunk_index)
    ).all()
    processed = 0
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        vectors = validate_vectors(
            embedder.encode([chunk.chunk_text for chunk in batch]), len(batch), embedder.dimension
        )
        for chunk, vector in zip(batch, vectors, strict=True):
            chunk.embedding = vector
            chunk.embedding_fingerprint = fingerprint
            chunk.embedded_at = now()
        session.commit()
        processed += len(batch)
    return processed
