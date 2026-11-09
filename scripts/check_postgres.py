"""Verify the isolated Docker database; never connect to host PostgreSQL on 5432."""

import argparse
import os
import subprocess
import sys
from uuid import uuid4

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

from peru_audit.config import Settings


def docker_database_url(value: str):
    url = make_url(value)
    if (
        url.drivername != "postgresql+psycopg"
        or url.host != "127.0.0.1"
        or url.port != 5433
        or url.database != "audit_intelligence"
    ):
        raise ValueError(
            "Se requiere PostgreSQL Docker en 127.0.0.1:5433/audit_intelligence. "
            "No se permite usar la instalación local del puerto 5432."
        )
    return url


def connect(url, database):
    return psycopg.connect(
        host=url.host,
        port=url.port,
        dbname=database,
        user=url.username,
        password=url.password,
        connect_timeout=5,
        autocommit=True,
    )


def check(url, integration=False):
    # Validation happens before opening any database connection.
    url = docker_database_url(url)
    with connect(url, url.database) as connection:
        version = int(connection.execute("SHOW server_version_num").fetchone()[0])
        if version // 10000 != 18:
            raise RuntimeError("El servidor del proyecto debe ser PostgreSQL 18")
        extension = connection.execute(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()
        if extension is None:
            raise RuntimeError("La extensión vector no está activada")
        distance = connection.execute("SELECT '[1,0]'::vector <=> '[1,0]'::vector").fetchone()[0]
        if abs(distance) > 1e-9:
            raise RuntimeError("La distancia coseno no produjo el resultado esperado")
        print(f"PostgreSQL 18 disponible en 5433; vector {extension[0]}; distancia coseno correcta")
    if not integration:
        return 0
    # A unique test database prevents synthetic fixtures from entering the real corpus.
    database = f"audit_intelligence_test_{uuid4().hex}"
    with connect(url, "postgres") as admin:
        admin.execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(database))
        )
        try:
            env = os.environ.copy()
            env["TEST_DATABASE_URL"] = url.set(database=database).render_as_string(
                hide_password=False
            )
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "-m", "postgres"],
                env=env,
                check=False,
            )
            return result.returncode
        finally:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--integration", action="store_true")
    args = parser.parse_args()
    try:
        return check(Settings().database_url, args.integration)
    except (ValueError, RuntimeError, psycopg.Error) as error:
        # Never print a DSN, password, environment or driver error containing connection details.
        print(
            f"Verificación PostgreSQL no completada ({type(error).__name__}). "
            "Revisa Docker, el healthcheck y la configuración local.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
