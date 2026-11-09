from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///data/local/audit.db"
    data_dir: Path = Path("data/raw")
    chunk_words: int = Field(default=180, ge=20, le=1000)
    chunk_overlap_words: int = Field(default=30, ge=0)
    ollama_url: str = "http://127.0.0.1:11434"
    embedding_model: str = "embeddinggemma"
    embedding_dimension: int = Field(default=768, ge=1, le=4096)
    llm_model: str = ""
    generation_enabled: bool = False
    min_semantic_score: float = Field(default=0.6, ge=-1, le=1)
    max_pdf_bytes: int = Field(default=25 * 1024 * 1024, ge=1024)
    max_pdf_pages: int = Field(default=500, ge=1)
    request_timeout: float = Field(default=120, gt=0)

    @model_validator(mode="after")
    def validate_settings(self):
        if self.chunk_overlap_words >= self.chunk_words:
            raise ValueError("chunk_overlap_words debe ser menor que chunk_words")
        if self.generation_enabled and not self.llm_model.strip():
            raise ValueError("Configura LLM_MODEL antes de habilitar generación")
        return self
