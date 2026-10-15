from enum import StrEnum


class ContactTitle(StrEnum):
    DR = "Dr"
    MR = "Mr"
    MS = "Ms"
    PROF = "Prof"


class JobType(StrEnum):
    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    CONTRACT = "Contract"
    PLACEMENT = "Placement"
    TEMPORARY = "Temporary"


class LetterStyle(StrEnum):
    DE = "de"
    UK = "uk"

    @classmethod
    def get_style(cls, country: str) -> "LetterStyle":
        try:
            return cls(country.lower())
        except ValueError:
            return cls.UK


class CVStyle(StrEnum):
    MODERN = "modern"
    CLASSIC = "classic"


class LLMProvider(StrEnum):
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENAI = "openai"
