import argparse
import json
import logging
import ssl
import sys
from pathlib import Path

import httpx
from pydantic import TypeAdapter

from peru_audit.api import json_default
from peru_audit.chunking import chunk_document
from peru_audit.config import Settings
from peru_audit.database import Database
from peru_audit.evaluation import EvaluationQuestion, evaluate
from peru_audit.ingestion import ingest_entry, read_manifest
from peru_audit.providers import OllamaEmbeddings
from peru_audit.quality import extraction_quality, write_quality
from peru_audit.retrieval import index_chunks, search
from peru_audit.schemas import SearchRequest


def main():
    parser = argparse.ArgumentParser(description="Peru Audit Intelligence: herramientas locales")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db")
    ingest = commands.add_parser("ingest")
    ingest.add_argument("manifest", type=Path)
    ingest.add_argument(
        "--extract-only",
        action="store_true",
        help="Registrar y extraer páginas sin crear chunks ni embeddings",
    )
    ingest.add_argument(
        "--use-cache",
        action="store_true",
        help="Reutilizar únicamente PDFs con hash y fecha original en el manifiesto",
    )
    quality = commands.add_parser("quality")
    quality.add_argument(
        "--output", type=Path, default=Path("data/results/extraction-quality.json")
    )
    quality.add_argument("--markdown", type=Path)
    commands.add_parser("index")
    chunk = commands.add_parser("chunk", help="Crear fragmentos desde páginas ya almacenadas")
    chunk.add_argument("--document-id", required=True)
    search_parser = commands.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--mode", choices=["keyword", "semantic"], default="keyword")
    search_parser.add_argument("--top-k", type=int, default=5)
    evaluation = commands.add_parser("evaluate")
    evaluation.add_argument("dataset", type=Path)
    evaluation.add_argument("--mode", choices=["keyword", "semantic"], default="keyword")
    evaluation.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # Do not log HTTP URLs or provider request bodies.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    settings = Settings()
    database = Database(settings.database_url)
    try:
        if args.command == "init-db":
            database.initialize()
            print("Base de datos inicializada")
            return
        with database.sessions() as session:
            if args.command == "ingest":
                entries = read_manifest(args.manifest)
                failed = 0
                with httpx.Client(
                    timeout=settings.request_timeout,
                    verify=ssl.create_default_context(),
                    headers={"User-Agent": "PeruAuditIntelligence/0.1"},
                ) as client:
                    for entry in entries:
                        try:
                            doc_id, status = ingest_entry(
                                session,
                                entry,
                                settings,
                                client,
                                create_chunks=not args.extract_only,
                                use_cache=args.use_cache,
                            )
                            print(json.dumps({"document_id": doc_id, "status": status}))
                        except Exception as error:
                            failed += 1
                            print(
                                json.dumps(
                                    {
                                        "report_number": entry.report_number,
                                        "error": type(error).__name__,
                                    }
                                ),
                                file=sys.stderr,
                            )
                if failed:
                    raise SystemExit(1)
            elif args.command == "quality":
                report = extraction_quality(session)
                write_quality(report, args.output, args.markdown)
                print(
                    json.dumps(
                        {
                            key: report[key]
                            for key in (
                                "document_count",
                                "page_count",
                                "pages_with_text",
                                "pages_flagged",
                            )
                        }
                    )
                )
            elif args.command == "chunk":
                try:
                    print(json.dumps(chunk_document(session, args.document_id, settings)))
                except ValueError as error:
                    print(str(error), file=sys.stderr)
                    raise SystemExit(1) from None
            elif args.command == "index":
                print(
                    json.dumps(
                        {"indexed_chunks": index_chunks(session, OllamaEmbeddings(settings))}
                    )
                )
            elif args.command == "search":
                request = SearchRequest(query=args.query, mode=args.mode, top_k=args.top_k)
                hits = search(
                    session,
                    request,
                    OllamaEmbeddings(settings) if args.mode == "semantic" else None,
                )
                print(json.dumps([hit.model_dump(mode="json") for hit in hits], ensure_ascii=False))
            elif args.command == "evaluate":
                questions = TypeAdapter(list[EvaluationQuestion]).validate_json(
                    args.dataset.read_text(encoding="utf-8")
                )
                result = evaluate(
                    session,
                    questions,
                    args.mode,
                    args.top_k,
                    OllamaEmbeddings(settings) if args.mode == "semantic" else None,
                )
                print(json.dumps(result, ensure_ascii=False, default=json_default, indent=2))
    finally:
        database.engine.dispose()


if __name__ == "__main__":
    main()
