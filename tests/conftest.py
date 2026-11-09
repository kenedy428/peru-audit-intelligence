from datetime import date
from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from peru_audit.config import Settings
from peru_audit.database import Chunk, Database, Document


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None, database_url=f"sqlite:///{tmp_path / 'test.db'}", data_dir=tmp_path / "raw"
    )


@pytest.fixture
def database(settings):
    database = Database(settings.database_url)
    database.initialize()
    yield database
    database.engine.dispose()


@pytest.fixture
def session(database):
    with database.sessions() as session:
        yield session


@pytest.fixture
def seeded(session):
    for index, (entity, year, texts) in enumerate(
        [
            (
                "Entidad sintética A",
                2024,
                [
                    "Control de accesos y seguridad de usuarios.",
                    "Los respaldos digitales se verifican cada semana.",
                ],
            ),
            ("Entidad sintética B", 2023, ["Control de accesos físicos del almacén."]),
        ],
        1,
    ):
        doc = Document(
            report_number=f"TEST-{index}",
            title=f"Documento sintético {index}",
            entity_name=entity,
            control_type="Visita de control",
            issue_date=date(year, 4, 19),
            publication_date=None,
            region="Lima",
            auditor=None,
            document_kind="report",
            source_url=f"https://apps8.contraloria.gob.pe/test-{index}.pdf",
            source_hash=str(index) * 64,
            local_path="not-a-real-pdf",
            processing_status="ready",
        )
        session.add(doc)
        session.flush()
        for number, text in enumerate(texts, 1):
            session.add(
                Chunk(
                    document_id=doc.document_id,
                    page_start=number,
                    page_end=number,
                    chunk_index=number - 1,
                    chunk_text=text,
                    char_start=0,
                    char_end=len(text),
                    word_count=len(text.split()),
                )
            )
    session.commit()
    return session


class FakeEmbedder:
    """Deterministic synthetic vectors: never a semantic quality benchmark."""

    dimension = 2
    fingerprint = "synthetic-fixture:v1:d2"

    def encode(self, texts):
        return [[1.0, 0.0] if "accesos" in text.lower() else [0.0, 1.0] for text in texts]


@pytest.fixture
def embedder():
    return FakeEmbedder()


def pdf_bytes(texts=("Synthetic backup evidence",)):
    """Small in-memory PDF fixture; never part of the official corpus."""
    writer = PdfWriter()
    for text in texts:
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        stream = DecodedStreamObject()
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream.set_data(f"BT /F1 12 Tf 50 700 Td ({escaped}) Tj ET".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
