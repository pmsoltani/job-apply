import json
from pathlib import Path
from typing import Self

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configs(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Paths ---
    BASE_DIR: Path = Path(__file__).parent.parent
    CV_DIR: Path = BASE_DIR.parent.parent / "cv"
    CONTEXT_DIR: Path = BASE_DIR / "context"
    PROMPTS_DIR: Path = BASE_DIR / "prompts"
    PARSER_PROMPT_FILE: Path = PROMPTS_DIR / "parser_prompt.md"
    GENERATOR_PROMPT_FILE: Path = PROMPTS_DIR / "generator_prompt.md"

    @computed_field
    @property
    def context_files(self) -> list[Path]:
        return sorted(self.CONTEXT_DIR.glob("*.md"))

    # --- Personal info ---
    FIRST_NAME: str = Field(...)
    LAST_NAME: str = Field(...)
    address: str = Field(...)

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.FIRST_NAME} {self.LAST_NAME}"

    # --- FastAPI ---
    FASTAPI_HOST: str = "0.0.0.0"
    FASTAPI_PORT: int = 8000

    # --- Jina ---
    JINA_BASE_URL: str = "https://r.jina.ai"
    TIMEOUT_SECONDS: int = 60

    # --- Airtable ---
    AIRTABLE_PAT: str = Field(...)
    AIRTABLE_BASE_ID: str = Field(...)
    CONTENT_BASE_URL: str = "https://content.airtable.com"
    AIRTABLE_SCHEMA_FILE: Path = BASE_DIR / "airtable_schema.json"

    @computed_field
    @property
    def tables(self) -> dict[str, str]:
        return json.loads(self.AIRTABLE_SCHEMA_FILE.read_text())["tables"]

    @computed_field
    @property
    def fields(self) -> dict[str, dict[str, str]]:
        return json.loads(self.AIRTABLE_SCHEMA_FILE.read_text())["fields"]

    # --- LLM ---
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str | None = None

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str | None = None

    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str | None = None

    MAX_TOKENS_PARSER: int = 2048
    MAX_TOKENS_GENERATOR: int = 4096

    @computed_field
    @property
    def active_llm(self) -> str:
        for provider in ("anthropic", "gemini", "openai"):
            api_key = getattr(self, f"{provider.upper()}_API_KEY")
            model = getattr(self, f"{provider.upper()}_MODEL")
            if api_key and model:
                return provider
        raise ValueError("No LLM configured. Set *_API_KEY and *_MODEL in .env")

    @model_validator(mode="after")
    def _validate_llm(self) -> Self:
        _ = self.active_llm
        return self


c = Configs()
