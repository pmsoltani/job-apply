import logging
from functools import lru_cache

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from src.configs import lc
from src.schemas import GeneratedContent


logger = logging.getLogger(__name__)

GENERATOR_PROMPT = lc.GENERATOR_PROMPT_FILE.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _load_context() -> str:
    """Load and concatenate personal context files. Cached for the process lifetime"""
    parts = [GENERATOR_PROMPT, "\n\n---\n\n# Personal Context\n"]
    for path in lc.context_files:
        if not path.exists():
            logger.warning("Context file not found, skipping: %s", path)
            continue
        parts.append(f"\n## {path.name}\n\n{path.read_text(encoding='utf-8')}")
    return "\n".join(parts)


def _model_settings(cache_instructions: bool = True) -> ModelSettings:
    """Return provider-appropriate ModelSettings"""
    if lc.generator_model.startswith("anthropic:"):
        from pydantic_ai.models.anthropic import AnthropicModelSettings

        return AnthropicModelSettings(
            max_tokens=lc.MAX_TOKENS_GENERATOR,
            anthropic_cache_instructions=cache_instructions,
        )
    return ModelSettings(max_tokens=lc.MAX_TOKENS_GENERATOR)


_agent = Agent(lc.generator_model, output_type=GeneratedContent)


@_agent.system_prompt
def _system_prompt() -> str:
    return _load_context()


async def generate_documents(job_prompt: str) -> GeneratedContent:
    """Pipeline 2: generate cover letter body + CV intro from the Airtable Prompt field."""
    result = await _agent.run(
        job_prompt,
        model_settings=_model_settings(cache_instructions=True),
        output_type=GeneratedContent,
    )
    assert isinstance(result.output, GeneratedContent)
    logger.info("Generated documents (usage: %s)", result.usage())
    return result.output
