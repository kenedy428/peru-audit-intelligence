import pytest
from sqlalchemy import select

from peru_audit.database import Chunk
from peru_audit.providers import ProviderUnavailable, validate_vectors
from peru_audit.retrieval import index_chunks, search
from peru_audit.schemas import Filters, SearchRequest


def test_keyword_search_applies_filters_before_ranking(seeded):
    hits = search(seeded, SearchRequest(query="control accesos", filters=Filters(year=2024)))
    assert len(hits) == 1
    assert hits[0].report_number == "TEST-1"
    assert hits[0].page_start == 1
    assert hits[0].score_type == "keyword_coverage"
    assert search(seeded, SearchRequest(query="zzzzsincoincidencia")) == []


def test_index_idempotency_and_model_isolation(seeded, embedder):
    assert index_chunks(seeded, embedder) == 3
    assert index_chunks(seeded, embedder) == 0
    hits = search(seeded, SearchRequest(query="control accesos", mode="semantic"), embedder)
    assert len(hits) == 3
    assert hits[0].score == pytest.approx(1)
    embedder.fingerprint = "different-model:d2"
    assert search(seeded, SearchRequest(query="control accesos", mode="semantic"), embedder) == []
    assert index_chunks(seeded, embedder) == 3


def test_invalid_batch_does_not_write_partial_embeddings(seeded, embedder):
    embedder.encode = lambda texts: [[1.0, 0.0]]
    with pytest.raises(ProviderUnavailable):
        index_chunks(seeded, embedder)
    assert all(chunk.embedding is None for chunk in seeded.scalars(select(Chunk)))


def test_similar_excludes_source_chunk(seeded, embedder):
    index_chunks(seeded, embedder)
    chunk = seeded.scalar(select(Chunk))
    hits = search(
        seeded,
        SearchRequest(query=chunk.chunk_text, mode="semantic"),
        embedder,
        exclude_chunk_id=chunk.chunk_id,
    )
    assert len(hits) == 2
    assert all(item.chunk_id != chunk.chunk_id for item in hits)


@pytest.mark.parametrize("vectors", [[[0, 0]], [[float("nan"), 1]], [[1, 2, 3]], []])
def test_invalid_vectors(vectors):
    with pytest.raises(ProviderUnavailable):
        validate_vectors(vectors, 1, 2)
