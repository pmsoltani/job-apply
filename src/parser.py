import logging
from pathlib import Path

from pydantic_ai import Agent

from src.configs import lc
from src.schemas import JobData


logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    Path(__file__).parent.parent / "prompts" / "parser_system.md"
).read_text(encoding="utf-8")

_agent = Agent(lc.parser_model, output_type=JobData, system_prompt=_SYSTEM_PROMPT)


async def extract_job(text: str) -> JobData:
    from pydantic_ai.settings import ModelSettings

    result = await _agent.run(
        text,
        model_settings=ModelSettings(max_tokens=lc.MAX_TOKENS_PARSER),
        output_type=JobData,
    )
    assert isinstance(result.output, JobData)
    logger.info(
        "Extracted job: %s @ %s", result.output.job_title, result.output.company.name
    )
    return result.output
