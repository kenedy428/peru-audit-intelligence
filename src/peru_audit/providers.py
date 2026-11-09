import math
import ssl
from functools import cached_property

import httpx

from peru_audit.config import Settings


class ProviderUnavailable(RuntimeError):
    pass


def validate_vectors(vectors: list, count: int, dimension: int) -> list[list[float]]:
    if len(vectors) != count:
        raise ProviderUnavailable("Cantidad incorrecta de embeddings")
    normalized = []
    for vector in vectors:
        if len(vector) != dimension or not all(math.isfinite(v) for v in vector):
            raise ProviderUnavailable("Embedding de dimensión o valores inválidos")
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0:
            raise ProviderUnavailable("Embedding nulo")
        normalized.append([float(v / norm) for v in vector])
    return normalized


class OllamaEmbeddings:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.dimension = settings.embedding_dimension

    @cached_property
    def fingerprint(self) -> str:
        try:
            with httpx.Client(
                timeout=self.settings.request_timeout, verify=ssl.create_default_context()
            ) as client:
                response = client.get(f"{self.settings.ollama_url}/api/tags")
                response.raise_for_status()
                name = self.settings.embedding_model
                name = name if ":" in name else f"{name}:latest"
                model = next(m for m in response.json()["models"] if m["name"] == name)
                return f"ollama:{name}:{model['digest']}:d{self.dimension}:normalize-v1"
        except (httpx.HTTPError, ValueError, KeyError, StopIteration) as error:
            raise ProviderUnavailable(
                "Ollama o el modelo de embeddings no están disponibles; revisa la configuración"
            ) from error

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            with httpx.Client(
                timeout=self.settings.request_timeout, verify=ssl.create_default_context()
            ) as client:
                response = client.post(
                    f"{self.settings.ollama_url}/api/embed",
                    json={
                        "model": self.settings.embedding_model,
                        "input": texts,
                        "dimensions": self.dimension,
                        "truncate": False,
                    },
                )
                response.raise_for_status()
                return validate_vectors(response.json()["embeddings"], len(texts), self.dimension)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            raise ProviderUnavailable("No fue posible generar embeddings locales") from error


class OllamaGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate(self, messages: list[dict], schema: dict) -> dict:
        try:
            with httpx.Client(
                timeout=self.settings.request_timeout, verify=ssl.create_default_context()
            ) as client:
                response = client.post(
                    f"{self.settings.ollama_url}/api/chat",
                    json={
                        "model": self.settings.llm_model,
                        "messages": messages,
                        "format": schema,
                        "stream": False,
                        "options": {"temperature": 0, "num_predict": 800},
                    },
                )
                response.raise_for_status()
                import json

                return json.loads(response.json()["message"]["content"])
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            raise ProviderUnavailable("El modelo local no devolvió una respuesta válida") from error
