import re
import unicodedata
import zlib
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError


@dataclass(frozen=True)
class ExtractedPage:
    number: int
    original_text: str
    text: str
    extraction_error: str | None = None


@dataclass(frozen=True)
class TextChunk:
    page_number: int
    char_start: int
    char_end: int
    text: str
    word_count: int


def clean_text(text: str) -> str:
    # Conservative normalization: preserve numbering, punctuation and letter case.
    normalized = unicodedata.normalize("NFC", text).replace("\x00", "")
    return re.sub(r"\s+", " ", normalized).strip()


def extract_pdf(path: Path, max_pages: int = 500) -> list[ExtractedPage]:
    reader = PdfReader(path)
    if reader.is_encrypted:
        raise ValueError("PDF cifrado: se requiere una versión pública sin cifrado")
    if not reader.pages or len(reader.pages) > max_pages:
        raise ValueError("Cantidad de páginas fuera del límite permitido")
    pages = []
    for number, page in enumerate(reader.pages, 1):
        try:
            original = page.extract_text() or ""
            pages.append(ExtractedPage(number, original, clean_text(original)))
        except (
            PyPdfError,
            ValueError,
            TypeError,
            KeyError,
            NotImplementedError,
            zlib.error,
        ) as error:
            # Keep the physical page slot; do not discard readable pages in the same PDF.
            pages.append(ExtractedPage(number, "", "", type(error).__name__))
    return pages


def chunk_pages(pages: list[ExtractedPage], size: int = 180, overlap: int = 30) -> list[TextChunk]:
    if size < 1 or not 0 <= overlap < size:
        raise ValueError("Se requiere 0 <= overlap < size")
    chunks = []
    for page in pages:
        words = list(re.finditer(r"\S+", page.text))
        start = 0
        while start < len(words):
            end = min(start + size, len(words))
            left, right = words[start].start(), words[end - 1].end()
            chunks.append(TextChunk(page.number, left, right, page.text[left:right], end - start))
            if end == len(words):
                break
            start = end - overlap
    return chunks
