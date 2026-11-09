import pytest
from pydantic import ValidationError

from peru_audit.evaluation import EvaluationQuestion, EvidenceReference, evaluate, metrics
from peru_audit.rag import FALLBACK, ask
from peru_audit.retrieval import index_chunks, search
from peru_audit.schemas import AskRequest, Filters, SearchRequest


class Generator:
    def __init__(self, payload):
        self.payload = payload

    def generate(self, messages, schema):
        assert "datos no confiables" in messages[0]["content"]
        return self.payload


def enable(settings):
    settings.generation_enabled = True
    settings.llm_model = "synthetic-test-model"
    return settings


def test_rag_uses_only_valid_citations(seeded, settings, embedder):
    index_chunks(seeded, embedder)
    response = ask(
        seeded,
        AskRequest(question="control accesos"),
        enable(settings),
        embedder,
        Generator(
            {"sufficient_evidence": True, "answer": "Hay controles [E1].", "evidence_ids": ["E1"]}
        ),
    )
    assert response.status == "answered"
    assert len(response.sources) == 1
    assert response.sources[0].source_hash


@pytest.mark.parametrize(
    "answer, ids",
    [("Texto sin cita", ["E1"]), ("Texto [E99]", ["E99"]), ("Texto [E1] y [E99]", ["E1"])],
)
def test_rag_rejects_invalid_citations(seeded, settings, embedder, answer, ids):
    index_chunks(seeded, embedder)
    response = ask(
        seeded,
        AskRequest(question="control accesos"),
        enable(settings),
        embedder,
        Generator({"sufficient_evidence": True, "answer": answer, "evidence_ids": ids}),
    )
    assert response.answer == FALLBACK
    assert response.sources == []


def test_rag_abstains_with_empty_index(seeded, settings, embedder):
    response = ask(seeded, AskRequest(question="control accesos"), enable(settings), embedder)
    assert response.status == "insufficient_evidence"


def test_recall_counts_distinct_evidence_not_repeated_chunks(seeded):
    hits = search(seeded, SearchRequest(query="control accesos", filters=Filters(year=2024)))
    references = [
        EvidenceReference(report_number="TEST-1", page=1),
        EvidenceReference(report_number="TEST-1", page=2),
    ]
    result = metrics([hits[0], hits[0]], references)
    assert result == {"recall_at_k": 0.5, "hit_at_k": 1, "reciprocal_rank": 1}


def test_evaluation_excludes_unanswerable_from_retrieval_averages(seeded):
    questions = [
        EvaluationQuestion(
            question_id="a",
            question="respaldos digitales",
            category="test",
            relevant=[EvidenceReference(report_number="TEST-1", page=2)],
        ),
        EvaluationQuestion(question_id="b", question="unknown", category="test", unanswerable=True),
    ]
    result = evaluate(seeded, questions, "keyword", 5)
    assert result["answerable_count"] == 1
    assert result["averages"]["recall_at_k"] == 1
    with pytest.raises(ValidationError):
        EvaluationQuestion(question_id="invalid", question="x", category="test")
