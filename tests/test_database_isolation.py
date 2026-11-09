import pytest

from scripts.check_postgres import docker_database_url


def test_docker_database_uses_only_dedicated_host_port():
    url = docker_database_url(
        "postgresql+psycopg://audit:synthetic@127.0.0.1:5433/audit_intelligence"
    )
    assert url.port == 5433
    assert url.database == "audit_intelligence"


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://audit:synthetic@localhost:5433/audit_intelligence",
        "postgresql+psycopg://audit:synthetic@127.0.0.1:5432/audit_intelligence",
        "postgresql+psycopg://audit:synthetic@127.0.0.1/audit_intelligence",
        "postgresql+psycopg://audit:synthetic@127.0.0.1:5433/postgres",
        "postgresql+psycopg://audit:synthetic@example.com:5433/audit_intelligence",
        "sqlite:///data/local/audit.db",
    ],
)
def test_database_check_rejects_local_or_unrelated_databases(url):
    with pytest.raises(ValueError):
        docker_database_url(url)
