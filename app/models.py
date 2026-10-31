from datetime import date
from typing import Literal

from pydantic import BaseModel, TypeAdapter


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


class LegalQuery(BaseModel):
    in_scope: bool
    scope_reason: str
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
    detail: str = ""
