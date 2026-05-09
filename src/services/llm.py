import logging

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from src.configs import c
from src.schemas import GeneratedContent, JobData


logger = logging.getLogger(__name__)


class LLMService:
    """Base class: builds the correct pydantic-ai model from Configs, with explicit API key."""

    def _build_model(self, model_name: str | None = None):
        provider = c.active_llm
        api_key: str = getattr(c, f"{provider.upper()}_API_KEY")
        name: str = model_name or getattr(c, f"{provider.upper()}_MODEL")

        if provider == "anthropic":
            from pydantic_ai.models.anthropic import AnthropicModel

            return AnthropicModel(name, api_key=api_key)
        if provider == "gemini":
            from pydantic_ai.models.google import GoogleModel

            return GoogleModel(name, api_key=api_key)
        if provider == "openai":
            from pydantic_ai.models.openai import OpenAIChatModel

            return OpenAIChatModel(name, api_key=api_key)
        raise ValueError(f"Unsupported LLM provider: {provider}")


class ParserService(LLMService):
    def __init__(self) -> None:
        model = self._build_model()
        prompt = c.PARSER_PROMPT_FILE.read_text(encoding="utf-8")
        self._agent: Agent[None, JobData] = Agent(
            model, output_type=JobData, system_prompt=prompt
        )

    async def extract_job(self, text: str, model: str | None = None) -> JobData:
        result = await self._agent.run(
            text,
            model=self._build_model(model) if model else None,
            model_settings=ModelSettings(max_tokens=c.MAX_TOKENS_PARSER),
            output_type=JobData,
        )
        assert isinstance(result.output, JobData)
        logger.info(
            "Extracted job: %s @ %s",
            result.output.job,
            result.output.company.name,
        )
        return result.output


class GeneratorService(LLMService):
    def __init__(self) -> None:
        model = self._build_model()
        self._agent: Agent[None, GeneratedContent] = Agent(
            model, output_type=GeneratedContent, system_prompt=self._load_context()
        )

    def _load_context(self) -> str:
        parts = [
            c.GENERATOR_PROMPT_FILE.read_text(encoding="utf-8"),
            "\n\n---\n\n# Personal Context\n",
        ]
        for path in c.context_files:
            if not path.exists():
                logger.warning("Context file not found, skipping: %s", path)
                continue
            parts.append(f"\n## {path.name}\n\n{path.read_text(encoding='utf-8')}")
        return "\n".join(parts)

    def _model_settings(self) -> ModelSettings:
        if c.active_llm == "anthropic":
            from pydantic_ai.models.anthropic import AnthropicModelSettings

            return AnthropicModelSettings(
                max_tokens=c.MAX_TOKENS_GENERATOR,
                anthropic_cache_instructions=True,
            )
        return ModelSettings(max_tokens=c.MAX_TOKENS_GENERATOR)

    async def generate_documents(
        self, job_prompt: str, model: str | None = None
    ) -> GeneratedContent:
        result = await self._agent.run(
            job_prompt,
            model=self._build_model(model) if model else None,
            model_settings=self._model_settings(),
            output_type=GeneratedContent,
        )
        assert isinstance(result.output, GeneratedContent)
        logger.info("Generated documents (usage: %s)", result.usage())
        return result.output
