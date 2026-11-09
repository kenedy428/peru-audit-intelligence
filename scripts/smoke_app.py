"""Bounded HTTP smoke check; never ingests synthetic data into the application corpus."""

import time

import httpx


def main():
    with httpx.Client(timeout=5) as client:
        for attempt in range(30):
            try:
                health = client.get("http://127.0.0.1:8000/api/v1/health")
                health.raise_for_status()
                client.get("http://127.0.0.1:8501/_stcore/health").raise_for_status()
                break
            except httpx.HTTPError:
                if attempt == 29:
                    raise
                time.sleep(1)
        for path in ("stats", "reports"):
            client.get(f"http://127.0.0.1:8000/api/v1/{path}").raise_for_status()
        response = client.post(
            "http://127.0.0.1:8000/api/v1/search", json={"query": "respaldos digitales"}
        )
        response.raise_for_status()
        assert isinstance(response.json()["results"], list)
        print("API, interfaz, listado y contrato de búsqueda disponibles")


if __name__ == "__main__":
    main()
