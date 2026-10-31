import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Final, Never, cast

from agent_framework import (
    AgentExecutor,
    AgentExecutorRequest,
    AgentExecutorResponse,
    FunctionExecutor,
    HistoryProvider,
    Message,
    SupportsChatGetResponse,
    Workflow,
    WorkflowBuilder,
    WorkflowContext,
    WorkflowEvent,
)
from agent_framework.exceptions import ChatClientContentFilterException, ChatClientException
from pydantic import BaseModel, ValidationError

from app.agents import analyst, brief, counsel
from app.config import cost_eur
from app.corpus import Corpus
from app.models import Answer, Citation, Draft, LegalQuery, PhaseEvent, Refusal, Step
from app.retrieval import Retriever

STEPS: dict[str, Step] = {"analyze": "analysing", "retrieve": "searching", "draft": "drafting", "verify": "verifying"}
FILTERED: Final = "content_filter"
MARKS = re.compile(r"\s*\[\d+\]")
HISTORY = 10
Routing = WorkflowContext[AgentExecutorRequest | Refusal, PhaseEvent]


def parsed[M: BaseModel](response: AgentExecutorResponse, model: type[M]) -> M | None:
    if (finish := response.agent_response.finish_reason) == FILTERED:
        return None
    if isinstance(value := response.agent_response.value, model):
        return value
    raise ValueError(f"{response.executor_id} returned no {model.__name__} (finish reason {finish})")


def in_scope(response: AgentExecutorResponse) -> bool:
    return (query := parsed(response, LegalQuery)) is not None and query.in_scope


def compose(draft: Draft, query: LegalQuery, citations: dict[str, Citation]) -> Answer | None:
    kept = [claim for claim in draft.claims if claim.article_ids and set(claim.article_ids) <= citations.keys()]
    if not kept:
        return None
    order = list(dict.fromkeys(block_id for claim in kept for block_id in claim.article_ids))
    marks = ["".join(f"[{order.index(b) + 1}]" for b in dict.fromkeys(claim.article_ids)) for claim in kept]
    return Answer(
        text="\n\n".join(f"{MARKS.sub('', claim.text)} {mark}" for claim, mark in zip(kept, marks, strict=True)),
        citations=[citations[block_id] for block_id in order],
        claims=len(kept),
        dropped_claims=len(draft.claims) - len(kept),
        language=query.language,
        facts_date=query.facts_date,
    )


def retrieval(search: Retriever, corpus: Corpus) -> FunctionExecutor:
    async def retrieve(response: AgentExecutorResponse, ctx: Routing) -> None:
        query = cast(LegalQuery, response.agent_response.value)
        chunks = await search(query.search_queries) if query.search_queries else []
        found = dict.fromkeys(block_id for chunk in chunks for block_id in corpus.locate(chunk.content))
        citations = {block_id: citation for block_id in found if (citation := corpus.cite(block_id, query.facts_date))}
        await ctx.yield_output(PhaseEvent(step="reading", articles=len(citations)))
        if not citations:
            await ctx.send_message(Refusal(reason="no_evidence"))
            return
        ctx.set_state("retrieved", (query, citations))
        conversation = response.full_conversation[: -len(response.agent_response.messages) or None]
        request = [*conversation, Message(role="user", contents=[brief(query, list(citations.values()))])]
        await ctx.send_message(AgentExecutorRequest(messages=request, should_respond=True))

    return FunctionExecutor(retrieve, id="retrieve")


async def verify(response: AgentExecutorResponse, ctx: WorkflowContext[Refusal, Answer]) -> None:
    drafted = parsed(response, Draft)
    if answer := compose(drafted, *ctx.get_state("retrieved")) if drafted else None:
        await ctx.yield_output(answer)
    else:
        await ctx.send_message(Refusal(reason="no_evidence" if drafted else FILTERED))


async def refuse(message: AgentExecutorResponse | Refusal, ctx: WorkflowContext[Never, Refusal]) -> None:
    if isinstance(message, AgentExecutorResponse):
        query = parsed(message, LegalQuery)
        message = Refusal(reason="out_of_scope", detail=query.scope_reason) if query else Refusal(reason=FILTERED)
    await ctx.yield_output(message)


def build(client: SupportsChatGetResponse[Any], search: Retriever, corpus: Corpus) -> Workflow:
    analyze, draft = AgentExecutor(analyst(client), id="analyze"), AgentExecutor(counsel(client), id="draft")
    retriever = retrieval(search, corpus)
    verifier, refuser = FunctionExecutor(verify, id="verify"), FunctionExecutor(refuse, id="refuse")
    return (
        WorkflowBuilder(start_executor=analyze, output_from=[verifier, refuser], intermediate_output_from=[retriever])
        .add_edge(analyze, retriever, condition=in_scope)
        .add_edge(analyze, refuser, condition=lambda response: not in_scope(response))
        .add_edge(retriever, draft)
        .add_edge(retriever, refuser)
        .add_edge(draft, verifier)
        .add_edge(verifier, refuser)
        .build()
    )


def count(usage: dict[str, int], event: WorkflowEvent[Any]) -> None:
    if event.executor_id == "retrieve":
        usage["searches"] = 1
    for sent in event.data or []:
        if isinstance(sent, AgentExecutorResponse):
            details = sent.agent_response.usage_details or {}
            usage[f"{event.executor_id}_input"] = details.get("input_token_count") or 0
            usage[f"{event.executor_id}_output"] = details.get("output_token_count") or 0


def declined(error: ChatClientException) -> bool:
    cause = error.__cause__.errors()[0] if isinstance(error.__cause__, ValidationError) else None
    prose = cause is not None and cause["type"] == "json_invalid" and not str(cause["input"]).lstrip().startswith("{")
    return isinstance(error, ChatClientContentFilterException) or prose


def transcript(answer: Answer) -> Message:
    sources = "; ".join(f"[{number}] {citation.title}" for number, citation in enumerate(answer.citations, 1))
    return Message(role="assistant", contents=[f"{answer.text}\n\nSources: {sources}"])


@dataclass
class Juriscope:
    client: SupportsChatGetResponse[Any]
    search: Retriever
    corpus: Corpus
    history: HistoryProvider
    model: str

    async def ask(self, session_id: str, question: str) -> AsyncIterator[PhaseEvent | Answer | Refusal]:
        asked = Message(role="user", contents=[question])
        messages = [*(await self.history.get_messages(session_id))[-HISTORY:], asked]
        usage: dict[str, int] = {}
        outcome: Answer | Refusal | None = None
        try:
            async for event in build(self.client, self.search, self.corpus).run(messages, stream=True):
                if event.type == "executor_invoked" and (step := STEPS.get(event.executor_id or "")):
                    yield PhaseEvent(step=step)
                elif event.type == "executor_completed":
                    count(usage, event)
                elif event.type == "intermediate":
                    yield event.data
                elif event.type == "output":
                    outcome = event.data
        except ChatClientException as error:
            if not declined(error):
                raise
            outcome = Refusal(reason=FILTERED)
        if outcome is None:
            raise RuntimeError("the workflow ended without an answer or a refusal")
        outcome = outcome.model_copy(update={"usage": usage, "cost_eur": cost_eur(self.model, usage)})
        if isinstance(outcome, Answer):
            await self.history.save_messages(session_id, [asked, transcript(outcome)])
        yield outcome
