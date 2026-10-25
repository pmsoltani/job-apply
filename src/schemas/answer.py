from pydantic import BaseModel, Field, computed_field

from src.schemas.common import RecordId, StrippedStr


_DESC_QUESTION = "The application form's question, including any length limit"
_DESC_RECORD_ID = "Job to tailor the answer to, if any"
_DESC_ANSWER = "The generated answer to the question"
_DESC_WORDS = "The number of words in the answer"
_DESC_CHARS = "The number of characters in the answer"


class AnswerPayload(BaseModel):
    question: StrippedStr = Field(..., min_length=10, description=_DESC_QUESTION)
    record_id: RecordId | None = Field(None, description=_DESC_RECORD_ID)


class AnswerResponse(AnswerPayload):
    answer: StrippedStr = Field(..., description=_DESC_ANSWER)

    @computed_field(description=_DESC_WORDS)
    @property
    def words(self) -> int:
        return len(self.answer.split())

    @computed_field(description=_DESC_CHARS)
    @property
    def chars(self) -> int:
        return len(self.answer)
