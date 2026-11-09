"""Check Git candidates without printing secret values."""

import re
import subprocess
from pathlib import Path

from dotenv import dotenv_values


def main():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={root.as_posix()}",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
        ],
        cwd=root,
        check=True,
        capture_output=True,
    )
    files = sorted(set(result.stdout.decode("utf-8").split("\0")) - {""})
    secrets = [
        value
        for key, value in dotenv_values(root / ".env").items()
        if value
        and len(value) >= 8
        and any(word in key.upper() for word in ("PASSWORD", "TOKEN", "SECRET", "API_KEY"))
    ]
    forbidden = ("data/raw/", "data/local/", "data/results/", ".venv/", "tmp/")
    pattern = re.compile(
        rb"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|"
        rb"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"
    )
    failures = []
    for name in files:
        path = root / name
        if (
            name == ".env"
            or name.startswith(forbidden)
            or path.suffix.lower() in (".pdf", ".db", ".sqlite", ".sqlite3", ".pem", ".key")
        ):
            failures.append(name)
            continue
        if not path.is_file():
            continue
        content = path.read_bytes()
        if pattern.search(content) or any(secret.encode() in content for secret in secrets):
            failures.append(name)
    if failures:
        print("Revisar candidatos (valores ocultos): " + ", ".join(failures))
        return 1
    print(
        f"{len(files)} archivos candidatos revisados; "
        "sin artefactos prohibidos ni secretos detectados"
    )
    print("Comprobación acotada: no sustituye una auditoría exhaustiva de secretos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
