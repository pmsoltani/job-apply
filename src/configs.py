import json
from pathlib import Path

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    BASE_DIR: Path = Path(__file__).parent.parent
    CV_DIR: Path = BASE_DIR.parent.parent / "cv"
    CLASSIC_CV_DIR: Path = CV_DIR / "classic"
    MODERN_CV_DIR: Path = CV_DIR / "modern"
    COVER_LETTER_DIR: Path = CV_DIR / "letter"

    FIRST_NAME: str = Field(...)
    LAST_NAME: str = Field(...)
    address: str = Field(...)

    @computed_field
    @property
    def full_name(self) -> str:
        if not self.FIRST_NAME or not self.LAST_NAME:
            raise ValueError("FIRST_NAME and/or LAST_NAME not set!")
        return f"{self.FIRST_NAME} {self.LAST_NAME}"

    FASTAPI_HOST: str = "0.0.0.0"
    FASTAPI_PORT: int = 8000

    JINA_BASE_URL: str = "https://r.jina.ai"
    TIMEOUT_SECONDS: int = 60


class AirtableConfig(BaseConfig):
    AIRTABLE_PAT: str = Field(...)
    AIRTABLE_BASE_ID: str = Field(...)

    CONTENT_BASE_URL: str = "https://content.airtable.com"

    SCHEMA_FILE: Path = Field(
        default_factory=lambda d: d["BASE_DIR"] / "airtable_schema.json"
    )
    SCHEMA: dict[str, dict] = Field(
        default_factory=lambda d: json.loads(d["SCHEMA_FILE"].read_text())
    )

    tables: dict[str, str] = Field(default_factory=lambda d: d["SCHEMA"]["tables"])
    fields: dict[str, dict[str, str]] = Field(
        default_factory=lambda d: d["SCHEMA"]["fields"]
    )


class LLMConfig(BaseConfig):
    LLMS: list[str] = ["anthropic", "gemini", "openai"]

    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str | None = None

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str | None = None

    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str | None = None

    MAX_TOKENS_PARSER: int = 2048
    MAX_TOKENS_GENERATOR: int = 4096

    CONTEXT_DIR: Path = Field(default_factory=lambda d: d["BASE_DIR"] / "context")
    PROMPTS_DIR: Path = Field(default_factory=lambda d: d["BASE_DIR"] / "prompts")

    @property
    def context_files(self) -> list[Path]:
        return sorted(self.CONTEXT_DIR.glob("*.md"))

    PARSER_PROMPT_FILE: Path = Field(
        default_factory=lambda d: d["PROMPTS_DIR"] / "parser_prompt.md"
    )
    GENERATOR_PROMPT_FILE: Path = Field(
        default_factory=lambda d: d["PROMPTS_DIR"] / "generator_prompt.md"
    )

    def _is_available(self, llm: str) -> bool:
        api_key = f"{llm.upper()}_API_KEY"
        model = f"{llm.upper()}_MODEL"
        return bool(getattr(self, api_key)) and bool(getattr(self, model))

    @computed_field
    @property
    def available(self) -> list[str]:
        return [llm for llm in self.LLMS if self._is_available(llm)]

    @computed_field
    @property
    def generator_model(self) -> str:
        return self.available[0]

    @computed_field
    @property
    def parser_model(self) -> str:
        return self.available[0]

    @model_validator(mode="after")
    def validate_llms(self):
        if not self.available:
            raise ValueError("No configured LLMs found!")
        return self


bc = BaseConfig()
ac = AirtableConfig()
lc = LLMConfig()
