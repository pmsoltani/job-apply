import logging
import time
from pathlib import Path

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
from src.schemas import GeneratedContent, JobBase, ModelCheckResponse


lg = logging.getLogger(c.APP_NAME)


class LLMService:
    """Base class: builds the correct pydantic-ai model from Configs, with explicit API key."""

    def _build_model(self, model_name: str) -> Model:
        url = str(c.LLM_URL) if c.LLM_URL else None
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

    async def check(self) -> list[ModelCheckResponse]:
        """Verify all models with a live check."""
        return [await self.check_model(m) for m in set(c.LLM_ALL_MODELS.values())]

    async def check_model(self, model: str) -> ModelCheckResponse:
        """Verify the configured provider, model, URL and key with a live check."""
        result = ModelCheckResponse(
            ok=False,
            provider=c.LLM_PROVIDER,
            model=model,
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
        lg.info("Model check (%s / %s): ok=%s", c.LLM_PROVIDER, model, result.ok)
        return result


class ParserService(LLMService):
    def __init__(self) -> None:
        model = self._build_model(c.LLM_PARSER_MODEL)
        prompt = c.PARSER_PROMPT_FILE.read_text(encoding="utf-8")
        # Self-hosted LLM might serialize nested objects (`company`) as JSON
        # strings in tool arguments, which fails validation. Asking for JSON in
        # the response body via `PromptedOutput` solves that.
        self._parser_agent: Agent[None, JobBase | str] = Agent(
            model, output_type=PromptedOutput(JobBase), system_prompt=prompt
        )

    async def parse(self, text: str, model: str | None = None) -> JobBase:
        result = await self._parser_agent.run(
            text,
            model=self._build_model(model) if model else None,
            model_settings=ModelSettings(max_tokens=c.MAX_TOKENS_PARSER),
        )
        assert isinstance(result.output, JobBase)
        lg.info("Parsed job (usage: %s)", result.usage)
        return result.output


class GeneratorService(LLMService):
    def __init__(self) -> None:
        model = self._build_model(c.LLM_GENERATOR_MODEL)
        context = self._load_context()
        self._generator_agent: Agent[None, GeneratedContent | str] = Agent(
            model,
            output_type=GeneratedContent,
            system_prompt=self._system_prompt(c.GENERATOR_PROMPT_FILE, context),
        )
        self._answer_agent: Agent[None, str] = Agent(
            model,
            output_type=str,
            system_prompt=self._system_prompt(c.ANSWER_PROMPT_FILE, context),
        )

    def _system_prompt(self, prompt_file: Path, context: str) -> str:
        """The agent's own instructions, then the shared writing rules and context."""
        parts = [
            prompt_file.read_text(encoding="utf-8"),
            c.WRITING_RULES_FILE.read_text(encoding="utf-8"),
            context,
        ]
        return "\n\n---\n\n".join(p.strip() for p in parts)

    def _load_context(self) -> str:
        parts = ["# Personal Context"]
        for path in c.context_files:
            if not path.exists():
                lg.warning("Context file not found, skipping: %s", path)
                continue
            content = path.read_text(encoding="utf-8")
            parts.append(f'<document name="{path.name}">\n{content}\n</document>')
        return "\n\n".join(p.strip() for p in parts)

    def _model_settings(self) -> ModelSettings:
        if c.LLM_PROVIDER == LLMProvider.ANTHROPIC:
            from pydantic_ai.models.anthropic import AnthropicModelSettings

            return AnthropicModelSettings(
                max_tokens=c.MAX_TOKENS_GENERATOR,
                anthropic_cache_instructions=True,
            )
        return ModelSettings(max_tokens=c.MAX_TOKENS_GENERATOR)

    async def generate(
        self, job_prompt: str, model: str | None = None
    ) -> GeneratedContent:
        result = await self._generator_agent.run(
            job_prompt,
            model=self._build_model(model) if model else None,
            model_settings=self._model_settings(),
        )
        assert isinstance(result.output, GeneratedContent)
        lg.info("Generated content (usage: %s)", result.usage)
        return result.output

    async def answer(self, prompt: str, model: str | None = None) -> str:
        result = await self._answer_agent.run(
            prompt,
            model=self._build_model(model) if model else None,
            model_settings=self._model_settings(),
        )
        assert isinstance(result.output, str)
        lg.info("Answered question (usage: %s)", result.usage)
        return result.output
