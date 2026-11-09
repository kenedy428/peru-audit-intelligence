from datetime import date
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


def official_url(value: str) -> str:
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    if (
        parsed.scheme != "https"
        or not (host == "contraloria.gob.pe" or host.endswith(".contraloria.gob.pe"))
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
    ):
        raise ValueError("Se requiere una URL HTTPS oficial de contraloria.gob.pe")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReportMetadata(StrictModel):
    report_number: str = Field(min_length=1, max_length=150)
    title: str = Field(min_length=1, max_length=1000)
    entity_name: str = Field(min_length=1, max_length=500)
    control_type: str = Field(min_length=1, max_length=200)
    issue_date: date | None = None
    publication_date: date | None = None
    region: str | None = Field(default=None, max_length=100)
    auditor: str | None = Field(default=None, max_length=500)
    source_url: str = Field(max_length=2000)
    document_kind: Literal["report", "summary"] = "report"

    _official = field_validator("source_url")(official_url)


class ManifestEntry(ReportMetadata):
    reviewed: bool = False
    expected_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    cached_downloaded_at: AwareDatetime | None = None


class Filters(StrictModel):
    entity: str | None = Field(default=None, min_length=1, max_length=500)
    year: int | None = Field(default=None, ge=1900, le=2100)
    region: str | None = Field(default=None, min_length=1, max_length=100)
    control_type: str | None = Field(default=None, min_length=1, max_length=200)
    document_ids: list[str] = Field(default_factory=list, max_length=200)


class SearchRequest(StrictModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    mode: Literal["keyword", "semantic"] = "keyword"
    filters: Filters = Field(default_factory=Filters)


class AskRequest(StrictModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)
    filters: Filters = Field(default_factory=Filters)


class SimilarRequest(StrictModel):
    chunk_id: str = Field(min_length=1, max_length=36)
    top_k: int = Field(default=5, ge=1, le=50)
    filters: Filters = Field(default_factory=Filters)


class SearchHit(BaseModel):
    chunk_id: str
    document_id: str
    report_number: str
    title: str
    entity_name: str
    document_kind: str
    publication_date: date | None
    issue_date: date | None
    page_start: int
    page_end: int
    char_start: int
    char_end: int
    text: str
    source_url: str
    source_hash: str
    score: float
    score_type: Literal["keyword_coverage", "cosine_similarity"]
