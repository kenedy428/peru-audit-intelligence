"""Reproducible extraction diagnostics; flags require human interpretation, not an LLM."""

import json
import re
import unicodedata
from collections import Counter
from datetime import UTC
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from peru_audit.database import Document, Page, now

QUALITY_VERSION = "page-quality-v1"
MIN_TEXT_CHARACTERS = 80
MIN_TEXT_WORDS = 15


def page_quality(page: Page, error: str | None = None) -> dict:
    text = page.page_text
    words = re.findall(r"\S+", text)
    suspect = sum(
        char == "\ufffd"
        or unicodedata.category(char) in ("Co", "Cs")
        or (unicodedata.category(char) == "Cc" and not char.isspace())
        for char in page.original_text
    )
    flags = []
    if error:
        flags.append("extraction_error")
    if not text:
        flags.append("no_text")
    elif len(text) < MIN_TEXT_CHARACTERS or len(words) < MIN_TEXT_WORDS:
        flags.append("sparse_text")
    if suspect or re.search(r"\(cid:\d+\)", text):
        flags.append("suspicious_encoding")
    letters = [word for word in words if word.isalpha()]
    if len(letters) >= 30 and sum(len(word) == 1 for word in letters) / len(letters) >= 0.4:
        flags.append("fragmented_text")
    return {
        "physical_page": page.page_number,
        "original_characters": len(page.original_text),
        "clean_characters": len(text),
        "word_count": len(words),
        "suspicious_characters": suspect,
        "flags": flags,
        "extraction_error": error,
    }


def extraction_quality(session: Session) -> dict:
    documents = []
    for doc in session.scalars(
        select(Document).order_by(Document.report_number, Document.source_hash)
    ):
        errors = doc.processing_config.get("extraction_errors", {})
        pages = [
            page_quality(page, errors.get(str(page.page_number)))
            for page in session.scalars(
                select(Page).where(Page.document_id == doc.document_id).order_by(Page.page_number)
            )
        ]
        flags = Counter(flag for page in pages for flag in page["flags"])
        documents.append(
            {
                "document_id": doc.document_id,
                "report_number": doc.report_number,
                "title": doc.title,
                "entity_name": doc.entity_name,
                "source_url": doc.source_url,
                "source_sha256": doc.source_hash,
                "downloaded_at": (
                    doc.downloaded_at
                    if doc.downloaded_at.tzinfo
                    else doc.downloaded_at.replace(tzinfo=UTC)
                ).isoformat(),
                "processing_status": doc.processing_status,
                "pipeline_version": doc.pipeline_version,
                "processing_config": doc.processing_config,
                "page_count": len(pages),
                "pages_with_text": sum(page["clean_characters"] > 0 for page in pages),
                "pages_flagged": sum(bool(page["flags"]) for page in pages),
                "flags": dict(sorted(flags.items())),
                "pages": pages,
            }
        )
    return {
        "generated_at": now().isoformat(),
        "quality_version": QUALITY_VERSION,
        "thresholds": {
            "minimum_characters": MIN_TEXT_CHARACTERS,
            "minimum_words": MIN_TEXT_WORDS,
            "fragmented_single_letter_fraction": 0.4,
            "fragmented_minimum_alphabetic_words": 30,
        },
        "document_count": len(documents),
        "page_count": sum(doc["page_count"] for doc in documents),
        "pages_with_text": sum(doc["pages_with_text"] for doc in documents),
        "pages_flagged": sum(doc["pages_flagged"] for doc in documents),
        "documents": documents,
        "limitations": [
            "Flags are heuristics, not a fidelity score or proof of extraction correctness.",
            "No text can mean a blank page, a scanned image or an extraction limitation.",
            "Text presence does not verify table layout, reading order or diagram contents.",
        ],
    }


def quality_markdown(report: dict) -> str:
    lines = [
        "# Calidad de extracción documental",
        "",
        f"Generado: {report['generated_at']} · Reglas: {report['quality_version']}",
        "",
        f"Informes: **{report['document_count']}** · Páginas: **{report['page_count']}** · "
        f"Con texto: **{report['pages_with_text']}** · "
        f"Con alertas: **{report['pages_flagged']}**.",
        "",
        "Las alertas son heurísticas para revisión humana. No son una puntuación de fidelidad.",
        "Todas las páginas son posiciones físicas del PDF, empezando en 1.",
        "",
        "| Informe | Páginas | Sin texto | Texto escaso | Error de extracción |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for doc in report["documents"]:
        flags = doc["flags"]
        number = doc["report_number"].replace("|", "\\|")
        lines.append(
            f"| {number} | {doc['page_count']} | {flags.get('no_text', 0)} | "
            f"{flags.get('sparse_text', 0)} | {flags.get('extraction_error', 0)} |"
        )
    lines.extend(["", "## Procedencia y páginas para revisión", ""])
    for doc in report["documents"]:
        lines.extend(
            [
                f"### {doc['report_number']}",
                "",
                doc["title"],
                "",
                f"Fuente: {doc['source_url']}",
                "",
                f"SHA-256: `{doc['source_sha256']}`",
                "",
                f"Descarga: {doc['downloaded_at']} · Estado: {doc['processing_status']}",
                "",
            ]
        )
        for page in doc["pages"]:
            if page["flags"]:
                lines.append(
                    f"- Página {page['physical_page']}: {', '.join(page['flags'])}; "
                    f"{page['clean_characters']} caracteres, {page['word_count']} palabras."
                )
        if not doc["pages_flagged"]:
            lines.append("Sin alertas automáticas; esto no reemplaza la revisión visual.")
        lines.append("")
    lines.extend(
        [
            "## Interpretación de alertas",
            "",
            "- `no_text`: sin texto; revisar si es página vacía, imagen o fallo del parser.",
            "- `sparse_text`: menos de 80 caracteres o 15 palabras; no implica un error.",
            "- `extraction_error`: falló esa página; las páginas legibles se conservaron.",
            "- `suspicious_encoding`: caracteres sospechosos o glifos sin mapear.",
            "- `fragmented_text`: abundan palabras de una letra; revisar lectura y orden.",
            "",
            "No se evalúan automáticamente tablas, gráficos, semántica ni orden de lectura.",
            "",
        ]
    )
    return "\n".join(lines)


def write_quality(report: dict, output: Path, markdown: Path | None = None):
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if markdown is not None:
        markdown.parent.mkdir(parents=True, exist_ok=True)
        markdown.write_text(quality_markdown(report), encoding="utf-8")
