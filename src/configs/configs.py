from pathlib import Path
from typing import Literal, Self, override

from pydantic import Field, HttpUrl, SecretStr, computed_field, model_validator
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    PyprojectTomlConfigSettingsSource,
    SettingsConfigDict,
)

from src.configs.enums import LLMProvider


_COUNTRY_CODES = {
    "GB": "UK",
}


class Configs(BaseSettings):
    model_config = SettingsConfigDict(
        pyproject_toml_table_header=("project",),
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    @override
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            PyprojectTomlConfigSettingsSource(settings_cls),
            DotEnvSettingsSource(settings_cls),
            env_settings,
        )

    # --- App info ---
    APP_NAME: str = Field(..., alias="name")
    APP_VERSION: str = Field(..., alias="version")
    APP_DESCRIPTION: str = Field(..., alias="description")
    APP_ENV: Literal["dev", "prod"] = Field("dev", alias="env")

    # --- Paths ---
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    CV_DIR: Path = BASE_DIR.parent / "cv"
    CONTEXT_DIR: Path = BASE_DIR / "context"
    PROMPTS_DIR: Path = BASE_DIR / "prompts"
    PARSER_PROMPT_FILE: Path = PROMPTS_DIR / "parser_prompt.md"
    GENERATOR_PROMPT_FILE: Path = PROMPTS_DIR / "generator_prompt.md"

    @computed_field
    @property
    def context_files(self) -> list[Path]:
        return sorted(self.CONTEXT_DIR.rglob("*.md"))

    # --- Personal info ---
    FIRST_NAME: str = Field(...)
    LAST_NAME: str = Field(...)
    address: str = Field(...)

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.FIRST_NAME} {self.LAST_NAME}"

    # --- FastAPI ---
    API_VERSION: Literal["v0"] = "v0"

    @computed_field
    @property
    def API_PREFIX(self) -> str:
        return f"/api/{self.API_VERSION}"

    FASTAPI_HOST: str = "0.0.0.0"
    FASTAPI_PORT: int = 8000
    CLOUDFLARE_TUNNEL: str | None = None

    # --- Jina ---
    JINA_BASE_URL: str = "https://r.jina.ai"
    TIMEOUT_SECONDS: int = 60

    # --- Airtable ---
    AIRTABLE_PAT: str = Field(...)
    AIRTABLE_BASE_ID: str = Field(...)
    CONTENT_BASE_URL: str = "https://content.airtable.com"
    # Table names or IDs ("tbl..."). Field names are the aliases in `src/schemas`.
    AIRTABLE_JOBS_TABLE: str = "Jobs"
    AIRTABLE_COMPANIES_TABLE: str = "Companies"
    AIRTABLE_CONTACTS_TABLE: str = "Contacts"

    COUNTRY_CODE_MAPPING: dict[str, str] = Field(default_factory=lambda: _COUNTRY_CODES)

    # --- LLM ---
    LLM_PROVIDER: LLMProvider = Field(...)
    LLM_API_KEY: SecretStr = SecretStr("not required")
    LLM_MODEL: str = Field(...)
    LLM_URL: HttpUrl | None = None

    # The parser echoes the job posting back verbatim in `notes`, so its output is
    # roughly as long as the posting itself; 2048 truncates mid-JSON.
    MAX_TOKENS_PARSER: int = 8192
    MAX_TOKENS_GENERATOR: int = 8192
    MODEL_CHECK_MAX_TOKENS: int = 512

    @model_validator(mode="after")
    def _validate_llm(self) -> Self:
        if not all([self.LLM_PROVIDER, self.LLM_MODEL]):
            raise ValueError("LLM_PROVIDER and LLM_MODEL must be set")
        return self


c = Configs()
