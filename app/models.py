from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, TypeAdapter


class ArticleVersion(BaseModel):
    norm: str
    published: date
    in_force: date
    text: str
    note: str | None = None


class Article(BaseModel):
    block_id: str
    title: str
    repealed: date | None = None
    versions: list[ArticleVersion]


ARTICLES = TypeAdapter(list[Article])


class Reference(BaseModel):
    block_id: str
    title: str
    url: str


class Citation(Reference):
    version: ArticleVersion
    current: ArticleVersion | None
    repealed: date | None
    see_also: list[Reference]


Scope = Literal["criminal_code", "case_law", "other_law", "not_legal"]


class LegalQuery(BaseModel):
    question: str
    scope: Scope
    search_queries: list[str]
    facts_date: date | None
    language: str


class Claim(BaseModel):
    text: str
    article_ids: list[str]


class Draft(BaseModel):
    claims: list[Claim]


Step = Literal["analysing", "searching", "reading", "drafting", "verifying"]


class PhaseEvent(BaseModel):
    step: Step
    articles: int | None = None


class Outcome(BaseModel):
    usage: dict[str, int] = {}
    cost_eur: float = 0.0


class Answer(Outcome):
    text: str
    citations: list[Citation]
    claims: int
    dropped_claims: int
    language: str
    facts_date: date | None


class Refusal(Outcome):
    reason: Literal["out_of_scope", "no_evidence", "content_filter"]
    scope: Scope | None = None


class Turn(BaseModel):
    id: str
    question: str
    asked: datetime
    outcome: Answer | Refusal


class ConversationSummary(BaseModel):
    id: str
    title: str
    updated: datetime


class Conversation(ConversationSummary):
    turns: list[Turn]


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class Feedback(BaseModel):
    turn_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    value: Literal["up", "down", "copy"]
