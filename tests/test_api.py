from fastapi.testclient import TestClient

from peru_audit.api import create_app


def test_health_reports_and_search(database, settings, seeded):
    with TestClient(create_app(settings, database)) as client:
        assert client.get("/api/v1/health").json()["status"] == "ok"
        assert client.get("/api/v1/stats").json()["documents"] == 2
        assert client.get("/api/v1/stats").json()["documents_with_chunks"] == 2
        assert client.get("/api/v1/stats").json()["indexed_chunks"] == 0
        response = client.get("/api/v1/reports", params={"year": 2024})
        assert response.json()["total"] == 1
        assert "local_path" not in response.json()["results"][0]
        response = client.post("/api/v1/search", json={"query": "respaldos digitales"})
        assert response.status_code == 200
        assert response.json()["results"][0]["page_start"] == 2
        assert client.get("/api/v1/reports/missing").status_code == 404
        assert client.get("/api/v1/reports", params={"entity": ""}).status_code == 422


def test_validation_and_disabled_generation(database, settings):
    with TestClient(create_app(settings, database)) as client:
        for payload in (
            {"query": " "},
            {"query": "x", "top_k": 0},
            {"query": "x", "filters": {"typo": "value"}},
        ):
            assert client.post("/api/v1/search", json=payload).status_code == 422
        response = client.post("/api/v1/ask", json={"question": "¿Qué ocurrió?"})
        assert response.status_code == 200
        assert response.json()["status"] == "generation_disabled"
        assert response.json()["sources"] == []


def test_missing_database_returns_actionable_error(tmp_path):
    from peru_audit.config import Settings

    settings = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path / 'empty.db'}")
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 503
        assert "init-db" in response.json()["detail"]
