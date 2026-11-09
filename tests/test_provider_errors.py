from fastapi.testclient import TestClient

from peru_audit.api import create_app
from peru_audit.providers import ProviderUnavailable


def test_unavailable_embeddings_return_503(database, settings, seeded, monkeypatch):
    def unavailable(self):
        raise ProviderUnavailable("Modelo local no disponible")

    monkeypatch.setattr("peru_audit.providers.OllamaEmbeddings.fingerprint", property(unavailable))
    with TestClient(create_app(settings, database)) as client:
        response = client.post("/api/v1/search", json={"query": "accesos", "mode": "semantic"})
        assert response.status_code == 503
        assert response.json()["detail"] == "Modelo local no disponible"
