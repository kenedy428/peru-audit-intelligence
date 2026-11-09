from types import SimpleNamespace

import pytest

from peru_audit.documents import ExtractedPage, chunk_pages, clean_text, extract_pdf
from tests.conftest import pdf_bytes


def test_pdf_extraction_preserves_physical_pages(tmp_path):
    path = tmp_path / "synthetic.pdf"
    path.write_bytes(pdf_bytes(("Evidence on first page", "Evidence on second page")))
    pages = extract_pdf(path)
    assert [(page.number, page.text) for page in pages] == [
        (1, "Evidence on first page"),
        (2, "Evidence on second page"),
    ]


def test_cleaning_preserves_numbers_and_accents():
    assert clean_text("  5.1\nInformacio\u0301n\tN.º 007\x00 ") == "5.1 Información N.º 007"


def test_chunks_map_exactly_to_pages_without_losing_tail():
    text = " ".join(str(index) for index in range(11))
    pages = [
        ExtractedPage(1, text, text),
        ExtractedPage(2, "", ""),
        ExtractedPage(3, "otra página", "otra página"),
    ]
    chunks = chunk_pages(pages, size=5, overlap=2)
    assert [chunk.text for chunk in chunks] == [
        "0 1 2 3 4",
        "3 4 5 6 7",
        "6 7 8 9 10",
        "otra página",
    ]
    for chunk in chunks:
        page = next(page for page in pages if page.number == chunk.page_number)
        assert page.text[chunk.char_start : chunk.char_end] == chunk.text


@pytest.mark.parametrize("size, overlap", [(0, 0), (5, 5), (5, -1)])
def test_invalid_chunk_configuration(size, overlap):
    with pytest.raises(ValueError):
        chunk_pages([], size, overlap)


def test_pdf_page_limit(tmp_path):
    path = tmp_path / "synthetic.pdf"
    path.write_bytes(pdf_bytes(("one", "two")))
    with pytest.raises(ValueError, match="páginas"):
        extract_pdf(path, max_pages=1)


def test_page_failure_preserves_other_pages_and_physical_numbering(monkeypatch):
    class FakePage:
        def __init__(self, text):
            self.text = text

        def extract_text(self):
            if self.text is None:
                raise ValueError("synthetic malformed content stream")
            return self.text

    reader = SimpleNamespace(
        is_encrypted=False, pages=[FakePage("first"), FakePage(None), FakePage("third")]
    )
    monkeypatch.setattr("peru_audit.documents.PdfReader", lambda path: reader)
    pages = extract_pdf("unused")
    assert [page.number for page in pages] == [1, 2, 3]
    assert [page.text for page in pages] == ["first", "", "third"]
    assert pages[1].extraction_error == "ValueError"
