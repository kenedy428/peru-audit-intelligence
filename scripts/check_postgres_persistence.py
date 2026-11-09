"""Non-destructive persistence check, recreating only the approved Docker PostgreSQL service."""

import json
import subprocess
from pathlib import Path
from uuid import uuid4

from psycopg import sql

from peru_audit.config import Settings
from scripts.check_postgres import connect, docker_database_url


def docker(*args):
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=True, timeout=180
    )
    return result.stdout.strip()


def snapshot():
    container_id = docker("compose", "ps", "-q", "postgres")
    if not container_id:
        raise RuntimeError("No existe un contenedor postgres en ejecución")
    state = json.loads(docker("inspect", "--format", "{{json .State}}", container_id))
    bindings = json.loads(
        docker("inspect", "--format", "{{json .HostConfig.PortBindings}}", container_id)
    )
    mounts = json.loads(docker("inspect", "--format", "{{json .Mounts}}", container_id))
    image_id = docker("inspect", "--format", "{{.Image}}", container_id)
    if state.get("Health", {}).get("Status") != "healthy":
        raise RuntimeError("El contenedor debe estar healthy")
    if bindings != {"5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "5433"}]}:
        raise RuntimeError("La publicación debe ser exclusivamente 127.0.0.1:5433")
    data_volume = next((m for m in mounts if m["Destination"] == "/var/lib/postgresql"), None)
    if not data_volume or data_volume.get("Name") != "audit-intelligence_postgres18_data":
        raise RuntimeError("El contenedor no usa el volumen persistente exclusivo esperado")
    services = docker("compose", "ps", "--services", "--status", "running").splitlines()
    if services != ["postgres"]:
        raise RuntimeError("Esta fase permite únicamente el servicio postgres")
    return {
        "container_id": container_id,
        "image_id": image_id,
        "health": "healthy",
        "port_bindings": bindings,
        "volume": data_volume["Name"],
    }


def main():
    url = docker_database_url(Settings().database_url)
    before = snapshot()
    database = f"audit_intelligence_persist_{uuid4().hex}"
    marker = uuid4().hex
    with connect(url, "postgres") as admin:
        admin.execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(database))
        )
    try:
        with connect(url, database) as probe:
            probe.execute("CREATE TABLE persistence_probe (marker text PRIMARY KEY, payload text)")
            probe.execute(
                "INSERT INTO persistence_probe VALUES (%s, %s)", (marker, "synthetic-only")
            )
            assert probe.execute(
                "SELECT payload FROM persistence_probe WHERE marker = %s", (marker,)
            ).fetchone() == ("synthetic-only",)
        docker(
            "compose",
            "up",
            "-d",
            "--no-deps",
            "--force-recreate",
            "--wait",
            "--wait-timeout",
            "120",
            "postgres",
        )
        after = snapshot()
        if before["container_id"] == after["container_id"]:
            raise RuntimeError("La prueba requiere un contenedor realmente recreado")
        if before["volume"] != after["volume"]:
            raise RuntimeError("El volumen cambió inesperadamente")
        with connect(url, database) as probe:
            rows = probe.execute("SELECT marker, payload FROM persistence_probe").fetchall()
            if rows != [(marker, "synthetic-only")]:
                raise RuntimeError("El marcador no persistió tras recrear el contenedor")
        receipt = {
            "before": before,
            "after": after,
            "marker_survived_recreation": True,
            "test_database": database,
            "test_database_removed": False,
        }
    finally:
        # Only the uniquely named synthetic probe is removed; never the project DB or volume.
        with connect(url, "postgres") as admin:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database)))
    receipt["test_database_removed"] = True
    output = Path("data/results/docker-persistence.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
