from pydantic import Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from peru_audit.database import Document, now
from peru_audit.retrieval import search
from peru_audit.schemas import Filters, SearchHit, SearchRequest, StrictModel


class EvidenceReference(StrictModel):
    report_number: str = Field(min_length=1)
    page: int = Field(ge=1)


class EvaluationQuestion(StrictModel):
    question_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    category: str = Field(min_length=1)
    split: str = "development"
    filters: Filters = Field(default_factory=Filters)
    relevant: list[EvidenceReference] = Field(default_factory=list)
    unanswerable: bool = False

    @model_validator(mode="after")
    def check_references(self):
        if self.unanswerable == bool(self.relevant):
            raise ValueError("Define referencias para respondibles; ninguna para no respondibles")
        return self


def metrics(hits: list[SearchHit], relevant: list[EvidenceReference]) -> dict:
    expected = {(item.report_number, item.page) for item in relevant}
    if not expected:
        raise ValueError("Recall y MRR requieren al menos una referencia relevante")
    found = set()
    first_rank = None
    for rank, result in enumerate(hits, 1):
        matches = {
            key
            for key in expected
            if key[0] == result.report_number and result.page_start <= key[1] <= result.page_end
        }
        if matches and first_rank is None:
            first_rank = rank
        found.update(matches)
    return {
        "recall_at_k": len(found) / len(expected),
        "hit_at_k": float(bool(found)),
        "reciprocal_rank": 1 / first_rank if first_rank else 0.0,
    }


def evaluate(
    session: Session, questions: list[EvaluationQuestion], mode: str, top_k: int, embedder=None
) -> dict:
    if not questions or len({q.question_id for q in questions}) != len(questions):
        raise ValueError("Se requiere un dataset no vacío con identificadores únicos")
    results = []
    for question in questions:
        hits = search(
            session,
            SearchRequest(
                query=question.question, filters=question.filters, mode=mode, top_k=top_k
            ),
            embedder,
        )
        result = {
            "question_id": question.question_id,
            "split": question.split,
            "retrieved_chunks": [hit.chunk_id for hit in hits],
        }
        if question.unanswerable:
            result["note"] = "Sin referencia: requiere evaluación separada de abstención en /ask"
        else:
            result.update(metrics(hits, question.relevant))
        results.append(result)
    answerable = [result for result in results if "recall_at_k" in result]
    averages = (
        {
            key: sum(row[key] for row in answerable) / len(answerable)
            for key in ("recall_at_k", "hit_at_k", "reciprocal_rank")
        }
        if answerable
        else {}
    )
    return {
        "evaluated_at": now().isoformat(),
        "corpus": [
            {
                "document_id": doc.document_id,
                "report_number": doc.report_number,
                "source_hash": doc.source_hash,
                "pipeline_version": doc.pipeline_version,
                "processing_config": doc.processing_config,
            }
            for doc in session.scalars(select(Document).order_by(Document.source_hash))
        ],
        "mode": mode,
        "top_k": top_k,
        "answerable_count": len(answerable),
        "embedding_fingerprint": embedder.fingerprint if embedder else None,
        "averages": averages,
        "results": results,
    }
