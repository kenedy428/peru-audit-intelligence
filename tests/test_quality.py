from peru_audit.database import Document, Page
from peru_audit.quality import extraction_quality, page_quality, quality_markdown, write_quality


def page(text, number=1):
    return Page(
        document_id="synthetic",
        page_number=number,
        original_text=text,
        page_text=text,
        has_text=bool(text),
    )


def test_no_text_and_extraction_error_are_distinct():
    assert page_quality(page(""))["flags"] == ["no_text"]
    result = page_quality(page(""), "ValueError")
    assert result["flags"] == ["extraction_error", "no_text"]
    assert result["extraction_error"] == "ValueError"


def test_sparse_text_is_a_review_flag_not_automatic_ocr():
    result = page_quality(page("Signed digitally"))
    assert result["flags"] == ["sparse_text"]
    assert result["word_count"] == 2


def test_encoding_and_fragmented_text_flags():
    result = page_quality(page("a " * 35 + "\ufffd\ue000"))
    assert "suspicious_encoding" in result["flags"]
    assert "fragmented_text" in result["flags"]
    assert result["suspicious_characters"] == 2


def test_report_retains_provenance_and_counts_physical_pages_once(session, tmp_path):
    doc = Document(
        report_number="SYNTHETIC",
        title="Synthetic fixture",
        entity_name="Test entity",
        control_type="Test",
        document_kind="report",
        source_url="https://apps8.contraloria.gob.pe/test.pdf",
        source_hash="1" * 64,
        local_path="unused",
        processing_status="partial_text",
        processing_config={"extraction_errors": {"2": "ValueError"}, "create_chunks": False},
    )
    session.add(doc)
    session.flush()
    for number, text in enumerate(["This is a synthetic sentence with enough words " * 5, ""], 1):
        item = page(text, number)
        item.document_id = doc.document_id
        session.add(item)
    session.commit()
    report = extraction_quality(session)
    assert report["document_count"] == 1 and report["page_count"] == 2
    assert report["pages_with_text"] == 1 and report["pages_flagged"] == 1
    result = report["documents"][0]
    assert result["source_sha256"] == "1" * 64
    assert result["flags"] == {"extraction_error": 1, "no_text": 1}
    assert result["pages"][1]["physical_page"] == 2
    assert "SHA-256" in quality_markdown(report)
    output = tmp_path / "quality.json"
    markdown = tmp_path / "quality.md"
    write_quality(report, output, markdown)
    assert output.is_file() and markdown.is_file()


def test_empty_registry_reports_zero_counts(session):
    report = extraction_quality(session)
    assert report["page_count"] == 0 and report["documents"] == []
