from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from src.services import AirtableService, GeneratorService, ParserService, TypstService


@lru_cache
def get_parser() -> ParserService:
    return ParserService()


@lru_cache
def get_generator() -> GeneratorService:
    return GeneratorService()


@lru_cache
def get_typst() -> TypstService:
    return TypstService()


def get_airtable() -> AirtableService:
    return AirtableService()


ParserDep = Annotated[ParserService, Depends(get_parser)]
GeneratorDep = Annotated[GeneratorService, Depends(get_generator)]
TypstDep = Annotated[TypstService, Depends(get_typst)]
AirtableDep = Annotated[AirtableService, Depends(get_airtable)]
