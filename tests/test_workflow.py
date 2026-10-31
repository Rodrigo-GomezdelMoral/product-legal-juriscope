from collections.abc import Sequence
from datetime import date
from typing import Any

import pytest
from agent_framework import HistoryProvider, Message
from agent_framework.exceptions import ChatClientContentFilterException, ChatClientException
from pydantic import ValidationError

from app.corpus import Corpus
from app.doubles import ModelDouble, Reply
from app.models import Answer, Claim, Draft, LegalQuery, PhaseEvent, Refusal
from app.retrieval import Chunk
from app.workflow import Juriscope


class DictHistory(HistoryProvider):
    def __init__(self) -> None:
        super().__init__("test")
        self.sessions: dict[str, list[Message]] = {}

    async def get_messages(self, session_id: str | None, **kwargs: Any) -> list[Message]:
        return list(self.sessions.get(session_id or "", []))

    async def save_messages(self, session_id: str | None, messages: Sequence[Message], **kwargs: Any) -> None:
        self.sessions.setdefault(session_id or "", []).extend(messages)


@pytest.fixture(scope="module")
def corpus() -> Corpus:
    return Corpus.load()


def query(**changes: Any) -> LegalQuery:
    fields = {
        "in_scope": True,
        "scope_reason": "",
        "search_queries": ["homicidio"],
        "facts_date": None,
        "language": "es",
    }
    return LegalQuery.model_validate(fields | changes)


def claims(*article_ids: list[str]) -> Draft:
    return Draft(claims=[Claim(text=f"Claim {n}.", article_ids=ids) for n, ids in enumerate(article_ids, 1)])


class Run:
    def __init__(self, corpus: Corpus, replies: dict[type, Reply], found: Sequence[str] = ("a138", "a142")) -> None:
        self.corpus, self.found, self.searched = corpus, found, list[list[str]]()
        self.client, self.history = ModelDouble(replies), DictHistory()
        self.juriscope = Juriscope(self.client, self.search, corpus, self.history, "gpt-5-mini")

    async def search(self, queries: list[str]) -> list[Chunk]:
        self.searched.append(queries)
        texts = {b: f"{a.title}\n{a.versions[-1].text}" for b, a in self.corpus.articles.items() if b in self.found}
        return [Chunk(chunk_id=b, content=texts.get(b, b), score=1.0, reranker_score=3.0) for b in self.found]

    async def ask(self, question: str = "¿Pena del homicidio?") -> list[PhaseEvent | Answer | Refusal]:
        return [event async for event in self.juriscope.ask("session", question)]

    def formats(self) -> list[type]:
        return [response_format for response_format, _ in self.client.calls]


async def test_claims_cite_retrieved_articles(corpus: Corpus) -> None:
    run = Run(corpus, {LegalQuery: query(), Draft: claims(["a138"], ["a142", "a138"])})
    *phases, answer = await run.ask()
    assert [p.step for p in phases if isinstance(p, PhaseEvent)] == [
        "analysing",
        "searching",
        "reading",
        "drafting",
        "verifying",
    ]
    assert isinstance(answer, Answer) and answer.text == "Claim 1. [1]\n\nClaim 2. [2][1]"
    assert [c.url.rsplit("#", 1)[1] for c in answer.citations] == ["a138", "a142"]
    assert answer.usage == {
        "searches": 1,
        "analyze_input": 1000,
        "analyze_output": 200,
        "draft_input": 1000,
        "draft_output": 200,
    }
    assert answer.cost_eur == round((2000 * 0.22 + 400 * 1.76) / 1e6 + 0.00176, 6)


async def test_answer_carries_full_articles(corpus: Corpus) -> None:
    run = Run(corpus, {LegalQuery: query(), Draft: claims(["a138"])})
    answer = (await run.ask())[-1]
    assert isinstance(answer, Answer) and answer.citations[0].title == "Artículo 138"
    assert answer.citations[0].version == corpus.articles["a138"].versions[-1]
    assert [r.block_id for r in answer.citations[0].see_also] == ["a140", "a550"]


async def test_facts_date_selects_version(corpus: Corpus) -> None:
    run = Run(corpus, {LegalQuery: query(facts_date=date(2014, 5, 15)), Draft: claims(["a139"])}, found=["a139"])
    answer = (await run.ask("¿Qué decía el artículo 139 en mayo de 2014?"))[-1]
    assert isinstance(answer, Answer) and answer.facts_date == date(2014, 5, 15)
    citation = answer.citations[0]
    assert (
        citation.version.norm == "BOE-A-1995-25444" and citation.current and citation.current.norm == "BOE-A-2015-3439"
    )
    brief = run.client.calls[-1][1][-1].text
    assert 'version="applicable" in_force="1996-05-24"' in brief and 'version="current" in_force="2015-07-01"' in brief


async def test_out_of_scope_refused_without_retrieval(corpus: Corpus) -> None:
    run = Run(corpus, {LegalQuery: query(in_scope=False, scope_reason="Case law is not in the Code.")})
    refusal = (await run.ask("¿Qué dice el Supremo sobre la legítima defensa?"))[-1]
    assert isinstance(refusal, Refusal) and (refusal.reason, refusal.detail) == (
        "out_of_scope",
        "Case law is not in the Code.",
    )
    assert run.searched == [] and run.formats() == [LegalQuery] and "searches" not in refusal.usage


async def test_no_evidence_refusal(corpus: Corpus) -> None:
    unmapped = Run(corpus, {LegalQuery: query()}, found=["texto que no está en el Código"])
    refusal = (await unmapped.ask())[-1]
    assert isinstance(refusal, Refusal) and refusal.reason == "no_evidence" and unmapped.formats() == [LegalQuery]
    empty = Run(corpus, {LegalQuery: query(), Draft: Draft(claims=[])})
    refusal = (await empty.ask())[-1]
    assert isinstance(refusal, Refusal) and refusal.reason == "no_evidence" and empty.formats() == [LegalQuery, Draft]
    no_queries = Run(corpus, {LegalQuery: query(search_queries=[])})
    refusal = (await no_queries.ask())[-1]
    assert isinstance(refusal, Refusal) and refusal.reason == "no_evidence" and no_queries.searched == []


async def test_unverified_claim_is_dropped(corpus: Corpus) -> None:
    written = Claim(text="Pena de prisión [2].", article_ids=["a138"])
    run = Run(corpus, {LegalQuery: query(), Draft: Draft(claims=[written, *claims(["a138", "a999"], []).claims])})
    answer = (await run.ask())[-1]
    assert isinstance(answer, Answer) and (answer.claims, answer.dropped_claims) == (1, 2)
    assert answer.text == "Pena de prisión. [1]"
    assert [c.block_id for c in answer.citations] == ["a138"]


async def test_all_claims_dropped_refused(corpus: Corpus) -> None:
    run = Run(corpus, {LegalQuery: query(), Draft: claims(["a999"], ["a140"])})
    refusal = (await run.ask())[-1]
    assert isinstance(refusal, Refusal) and refusal.reason == "no_evidence"


def parse_failure(text: str) -> ChatClientException:
    try:
        LegalQuery.model_validate_json(text)
    except ValidationError as cause:
        error = ChatClientException("service failed to complete the prompt")
        error.__cause__ = cause
    return error


@pytest.mark.parametrize(
    "replies",
    [
        {LegalQuery: parse_failure("I'm sorry, but I cannot assist with that request.")},
        {LegalQuery: ChatClientContentFilterException("filtered")},
        {LegalQuery: "content_filter"},
        {LegalQuery: query(), Draft: ChatClientContentFilterException("filtered")},
        {LegalQuery: query(), Draft: "content_filter"},
    ],
)
async def test_content_filter_refusal(corpus: Corpus, replies: dict[type, Reply]) -> None:
    run = Run(corpus, replies)
    refusal = (await run.ask())[-1]
    assert isinstance(refusal, Refusal) and refusal.reason == "content_filter"
    assert run.history.sessions == {}


async def test_other_client_errors_propagate(corpus: Corpus) -> None:
    wrong_field = query().model_dump_json().replace('"facts_date":null', '"facts_date":"mayo de 2014"')
    for error in (
        parse_failure('{"in_scope": true, "scope_re'),
        parse_failure(wrong_field),
        ChatClientException("429"),
    ):
        with pytest.raises(ChatClientException):
            await Run(corpus, {LegalQuery: error}).ask()


@pytest.mark.parametrize("replies", [{LegalQuery: "length"}, {LegalQuery: query(), Draft: "length"}])
async def test_truncated_reply_is_an_error(corpus: Corpus, replies: dict[type, Reply]) -> None:
    with pytest.raises(ValueError, match="finish reason length"):
        await Run(corpus, replies).ask()


async def test_follow_up_uses_history(corpus: Corpus) -> None:
    run = Run(corpus, {LegalQuery: query(), Draft: claims(["a138"])})
    await run.ask("¿Pena del homicidio?")
    await run.ask("¿Y si concurre alevosía?")
    follow_up = run.client.calls[2][1]
    assert [m.role for m in follow_up] == ["user", "assistant", "user"]
    assert follow_up[1].text == "Claim 1. [1]\n\nSources: [1] Artículo 138"
    assert len(run.history.sessions["session"]) == 4
