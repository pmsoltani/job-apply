import logging
import time

from pydantic_ai import Agent, PromptedOutput
from pydantic_ai.exceptions import (
    ModelAPIError,
    ModelHTTPError,
    UnexpectedModelBehavior,
    UserError,
)
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

from src.configs import LLMProvider, c
from src.schemas import GeneratedContent, JobData, ModelCheckResponse


lg = logging.getLogger(c.APP_NAME)


class LLMService:
    """Base class: builds the correct pydantic-ai model from Configs, with explicit API key."""

    def _build_model(self, model_name: str | None = None) -> Model:
        url = str(c.LLM_URL) if c.LLM_URL else None
        model_name = model_name or c.LLM_MODEL
        key = c.LLM_API_KEY.get_secret_value()
        if c.LLM_PROVIDER == LLMProvider.ANTHROPIC:
            from pydantic_ai.models.anthropic import AnthropicModel
            from pydantic_ai.providers.anthropic import AnthropicProvider

            provider = AnthropicProvider(api_key=key, base_url=url)
            return AnthropicModel(model_name, provider=provider)
        if c.LLM_PROVIDER == LLMProvider.GOOGLE:
            from pydantic_ai.models.google import GoogleModel
            from pydantic_ai.providers.google import GoogleProvider

            provider = GoogleProvider(api_key=key, base_url=url)
            return GoogleModel(model_name, provider=provider)
        if c.LLM_PROVIDER == LLMProvider.OPENAI:
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.openai import OpenAIProvider

            provider = OpenAIProvider(api_key=key, base_url=url)
            return OpenAIChatModel(model_name, provider=provider)
        raise ValueError(f"Unsupported LLM provider: {c.LLM_PROVIDER}")

    async def check(self, model: str | None = None) -> ModelCheckResponse:
        """Verify the configured provider, model, URL and key with a live check."""
        model_name = model or c.LLM_MODEL
        result = ModelCheckResponse(
            ok=False,
            provider=c.LLM_PROVIDER,
            model=model_name,
            url=str(c.LLM_URL) if c.LLM_URL else None,
        )
        started = time.perf_counter()
        try:
            agent: Agent[None, str] = Agent(self._build_model(model), output_type=str)
            # Generous cap: reasoning models spend tokens thinking before they answer,
            # and a token-limit abort would look like a config failure.
            run = await agent.run(
                "Reply with the single word: pong",
                model_settings=ModelSettings(max_tokens=c.MODEL_CHECK_MAX_TOKENS),
            )
        except ModelHTTPError as exc:
            result.error = f"{type(exc).__name__}: {exc}"
            result.status_code = exc.status_code
        except (ModelAPIError, UnexpectedModelBehavior, UserError, ValueError) as exc:
            result.error = f"{type(exc).__name__}: {exc}"
        else:
            result.ok = True
            result.reply = run.output.strip()[:100]
        result.latency_ms = int((time.perf_counter() - started) * 1000)
        lg.info("Model check (%s / %s): ok=%s", c.LLM_PROVIDER, model_name, result.ok)
        return result


class ParserService(LLMService):
    def __init__(self) -> None:
        model = self._build_model()
        prompt = c.PARSER_PROMPT_FILE.read_text(encoding="utf-8")
        # Self-hosted LLM might serialize nested objects (`company`) as JSON
        # strings in tool arguments, which fails validation. Asking for JSON in
        # the response body via `PromptedOutput` solves that.
        self._agent: Agent[None, JobData | str] = Agent(
            model, output_type=PromptedOutput(JobData), system_prompt=prompt
        )

    async def extract_job_data(self, text: str, model: str | None = None) -> JobData:
        result = await self._agent.run(
            text,
            model=self._build_model(model) if model else None,
            model_settings=ModelSettings(max_tokens=c.MAX_TOKENS_PARSER),
        )
        assert isinstance(result.output, JobData)
        lg.info("Extracted job: %s @ %s", result.output.job, result.output.company.name)
        return result.output


class GeneratorService(LLMService):
    def __init__(self) -> None:
        model = self._build_model()
        self._agent: Agent[None, GeneratedContent | str] = Agent(
            model, output_type=GeneratedContent, system_prompt=self._load_context()
        )

    def _load_context(self) -> str:
        parts = [
            c.GENERATOR_PROMPT_FILE.read_text(encoding="utf-8"),
            "\n\n---\n\n# Personal Context\n",
        ]
        for path in c.context_files:
            if not path.exists():
                lg.warning("Context file not found, skipping: %s", path)
                continue
            parts.append(f"\n## {path.name}\n\n{path.read_text(encoding='utf-8')}")
        return "\n".join(parts)

    def _model_settings(self) -> ModelSettings:
        if c.LLM_PROVIDER == LLMProvider.ANTHROPIC:
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
        )
        assert isinstance(result.output, GeneratedContent)
        lg.info("Generated documents (usage: %s)", result.usage())
        return result.output
