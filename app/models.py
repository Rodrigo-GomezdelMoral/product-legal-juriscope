import re
import unicodedata
from datetime import date, datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, TypeAdapter, field_validator, model_validator

RUN, SHORT = 8, 4
QUOTES = "\"'\u201c\u201d\u00ab\u00bb\u2018\u2019"
ANY_QUOTE = {ord(quote): f"[{QUOTES}]" for quote in QUOTES}


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


def words(text: str) -> list[str]:
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", text).casefold())


def squash(text: str) -> str:
    return "".join(words(text))


def cut(text: str, passage: str) -> str:
    body = r"\s+".join(re.escape(part).translate(ANY_QUOTE) for part in passage.split())
    edges = (r"(?<!\w)" if passage[0].isalnum() else "", r"(?!\w)" if passage[-1].isalnum() else "")
    return re.sub(edges[0] + body + edges[1], " ", text)


def runs(passage: str, known: frozenset[str]) -> set[str]:
    found = words(passage)
    text, foreign = "".join(found), [word not in known for word in found for _ in word]
    return {text[i : i + RUN] for i in range(len(text) - RUN + 1) if any(foreign[i : i + RUN])}


class LegalQuery(BaseModel):
    left_out: list[str]
    question: str
    scope: Scope
    search_queries: list[str]
    facts_date: date | None
    language: str

    @field_validator("language")
    @classmethod
    def two_letters(cls, language: str) -> str:
        if not re.fullmatch(r"[a-z]{2}", language := language.strip().lower()):
            raise ValueError(f"not an ISO 639-1 code: {language[:20]}")
        return language

    @model_validator(mode="after")
    def only_the_legal_question(self) -> Self:
        for passage in sorted((p.strip() for p in self.left_out if len(squash(p)) >= SHORT), key=len, reverse=True):
            self.question = cut(self.question, passage)
        self.question = " ".join(self.question.split())
        if not squash(self.question):
            self.scope, self.search_queries = "not_legal", []
        return self

    def within(self, asked: str) -> Self:
        return self.model_copy(update={"left_out": [p for p in self.left_out if squash(p) in squash(asked)]})

    def repeated_in(self, text: str, known: frozenset[str]) -> bool:
        said, known = squash(text), known | set(words(self.question))
        return any(run in said for passage in self.left_out for run in runs(passage, known))


class Claim(BaseModel):
    text: str
    article_ids: list[str]

    def verified(self, query: LegalQuery, citations: dict[str, Citation], known: frozenset[str]) -> bool:
        cited = bool(self.article_ids) and set(self.article_ids) <= citations.keys()
        return cited and not query.repeated_in(self.text, known)


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
    question: str = Field("", exclude=True)


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
