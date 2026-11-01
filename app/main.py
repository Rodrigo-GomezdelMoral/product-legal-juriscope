import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Annotated, Any, cast
from uuid import uuid4

from agent_framework.exceptions import AgentFrameworkException
from agent_framework_azure_cosmos import CosmosHistoryProvider
from azure.core.exceptions import AzureError
from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity.aio import DefaultAzureCredential
from fastapi import Depends, FastAPI, HTTPException, Path, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from fastapi.staticfiles import StaticFiles
from openai import APIStatusError
from opentelemetry import trace
from opentelemetry.trace import StatusCode
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import telemetry
from app.agents import chat_client
from app.auth import User, signed_in
from app.config import Settings
from app.conversations import Conversations, emulator
from app.corpus import DATA, Corpus
from app.doubles import ModelDouble
from app.models import Answer, Conversation, ConversationSummary, Feedback, PhaseEvent, Question, Refusal, Turn
from app.retrieval import SearchRetriever, SearchUnavailableError
from app.workflow import Juriscope, UnusableReplyError, throttled

RETRY_AFTER_SECONDS = 20
FAILURES = (AgentFrameworkException, AzureError, UnusableReplyError)
NOTICE = (
    "Basado en datos de la Agencia Estatal Boletín Oficial del Estado. "
    "Texto consolidado de carácter meramente informativo."
)
Event = PhaseEvent | Answer | Refusal
ConversationId = Annotated[str, Path(pattern=r"^([0-9a-f]{32}|new)$")]


@dataclass
class Services:
    juriscope: Juriscope
    conversations: Conversations
    clear: Callable[[str], Awaitable[None]]
    meta: dict[str, str]


@dataclass
class Asking:
    user: User
    conversation_id: str
    title: str | None
    turn: dict[str, Any]
    events: AsyncIterator[Event]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings, corpus = Settings(), Corpus.load()
    updated = json.loads((DATA / "manifest.json").read_text("utf-8"))["updated"]
    async with (
        DefaultAzureCredential() as credential,
        CosmosClient(settings.cosmos_endpoint, settings.cosmos_key or credential, connection_timeout=5) as cosmos,
    ):
        name = settings.cosmos_database
        database = await emulator(cosmos, name) if settings.cosmos_key else cosmos.get_database_client(name)
        history = CosmosHistoryProvider(container_client=database.get_container_client("history"))
        retriever = SearchRetriever(settings.search_endpoint, settings.search_index, credential)
        client = ModelDouble() if settings.model_double else chat_client(settings, credential)
        juriscope = Juriscope(client, retriever.search, corpus, history, settings.chat_model)
        meta = {"updated": updated, "chat_model": settings.chat_model, "embedding_model": settings.embedding_model}
        conversations = Conversations(database.get_container_client("conversations"))
        app.state.services = Services(juriscope, conversations, history.clear, meta | {"notice": NOTICE})
        yield
        await retriever.close()


telemetry.configure()
app = FastAPI(title="Juriscope", lifespan=lifespan)


def services(request: Request) -> Services:
    return cast(Services, request.app.state.services)


Signed = Annotated[User, Depends(signed_in)]
Using = Annotated[Services, Depends(services)]


def problem(status: int, detail: str, retry_after: int | None = None) -> dict[str, Any]:
    trace_id = format(trace.get_current_span().get_span_context().trace_id, "032x")
    body = {"type": "about:blank", "title": HTTPStatus(status).phrase, "status": status, "detail": detail}
    return body | {"trace_id": trace_id} | ({"retry_after": retry_after} if retry_after else {})


def respond(body: dict[str, Any]) -> JSONResponse:
    headers = {"Retry-After": str(body["retry_after"])} if "retry_after" in body else None
    return JSONResponse(body, body["status"], headers, media_type="application/problem+json")


def retry_after(error: Exception) -> int:
    cause = error.__cause__
    header = cause.response.headers.get("retry-after", "") if isinstance(cause, APIStatusError) else ""
    return int(header) if header.isdigit() else RETRY_AFTER_SECONDS


def classify(error: Exception) -> tuple[int, str, int | None]:
    if throttled(error):
        return 503, "The language model is at capacity. Try again shortly.", retry_after(error)
    if isinstance(error, CosmosResourceNotFoundError):
        return 404, "The conversation was deleted.", None
    if isinstance(error, SearchUnavailableError):
        return 503, "Search over the Criminal Code is unavailable. Try again shortly.", RETRY_AFTER_SECONDS
    if isinstance(error, AzureError):
        return 503, "Conversation storage is unavailable. Try again shortly.", RETRY_AFTER_SECONDS
    if isinstance(error, UnusableReplyError):
        return 502, "The language model returned an unusable reply. Try again or rephrase the question.", None
    if isinstance(error.__cause__, APIStatusError) and error.__cause__.status_code < 500:
        return 502, "The language model rejected the request.", None
    return 503, "The language model is unavailable. Try again shortly.", RETRY_AFTER_SECONDS


def failure(error: Exception) -> dict[str, Any]:
    span = trace.get_current_span()
    span.record_exception(error)
    span.set_status(StatusCode.ERROR, type(error).__name__)
    return problem(*classify(error))


async def failed(request: Request, error: Exception) -> JSONResponse:
    return respond(failure(error))


async def unexpected(request: Request, error: Exception) -> JSONResponse:
    return respond(problem(500, "Juriscope failed unexpectedly. The trace id identifies the failure."))


@app.exception_handler(StarletteHTTPException)
async def refused(request: Request, error: StarletteHTTPException) -> JSONResponse:
    return respond(problem(error.status_code, str(error.detail)))


@app.exception_handler(RequestValidationError)
async def invalid(request: Request, error: RequestValidationError) -> JSONResponse:
    return respond(problem(422, "; ".join(str(issue["msg"]) for issue in error.errors())))


for kind in FAILURES:
    app.add_exception_handler(kind, failed)
app.add_exception_handler(500, unexpected)


@app.get("/healthz")
async def healthz(using: Using) -> dict[str, str]:
    await using.conversations.ping()
    return {"status": "ok"}


@app.get("/api/me")
async def me(user: Signed) -> dict[str, str]:
    return {"name": user.name, "initials": "".join(word[0] for word in user.name.split()[:2]).upper()}


@app.get("/api/meta")
async def meta(user: Signed, using: Using) -> dict[str, str]:
    return using.meta


@app.get("/api/conversations")
async def conversations(user: Signed, using: Using) -> list[ConversationSummary]:
    return await using.conversations.summaries(user.id)


async def owned(using: Services, user: User, conversation_id: str) -> Conversation:
    if found := await using.conversations.get(user.id, conversation_id):
        return found
    raise HTTPException(404, "No such conversation.")


@app.get("/api/conversations/{conversation_id}")
async def conversation(conversation_id: ConversationId, user: Signed, using: Using) -> Conversation:
    return await owned(using, user, conversation_id)


async def forget(using: Services, user: User, conversation_id: str) -> None:
    await using.clear(conversation_id)
    await using.conversations.delete(user.id, conversation_id)


@app.delete("/api/conversations/{conversation_id}", status_code=204)
async def delete(conversation_id: ConversationId, user: Signed, using: Using) -> None:
    await owned(using, user, conversation_id)
    await forget(using, user, conversation_id)


@app.delete("/api/conversations", status_code=204)
async def delete_all(user: Signed, using: Using) -> None:
    for summary in await using.conversations.summaries(user.id):
        await forget(using, user, summary.id)


@app.post("/api/feedback", status_code=204)
async def feedback(body: Feedback, user: Signed) -> None:
    if body.value != "copy":
        telemetry.event("FeedbackGiven", user.id, turn_id=body.turn_id, value=body.value)
    if body.value != "down":
        telemetry.event("AnswerAccepted", user.id, turn_id=body.turn_id, via=body.value)


async def start(conversation_id: ConversationId, body: Question, user: Signed, using: Using) -> Asking:
    title = body.question[:80] if conversation_id == "new" else None
    if title is None:
        await owned(using, user, conversation_id)
    conversation_id = uuid4().hex if title else conversation_id
    turn: dict[str, Any] = {"id": uuid4().hex, "question": body.question, "asked": datetime.now(UTC)}
    telemetry.event("QuestionAsked", user.id, turn_id=turn["id"])
    events = using.juriscope.ask(conversation_id, body.question)
    head = [await anext(events)]
    while head[-1] == PhaseEvent(step="analysing"):
        head.append(await anext(events))
    return Asking(user, conversation_id, title, turn, chain(head, events))


async def chain(head: list[Event], rest: AsyncIterator[Event]) -> AsyncIterator[Event]:
    for event in head:
        yield event
    async for event in rest:
        yield event


@app.post("/api/conversations/{conversation_id}/messages", response_class=EventSourceResponse)
async def ask(asking: Annotated[Asking, Depends(start)], using: Using) -> AsyncIterator[ServerSentEvent]:
    try:
        async for event in asking.events:
            if isinstance(event, PhaseEvent):
                yield ServerSentEvent(event="phase", data=event)
                continue
            turn = Turn(**asking.turn, outcome=event)
            await using.conversations.add(asking.user.id, asking.conversation_id, turn, asking.title)
            telemetry.delivered(asking.user.id, turn)
            kind = "answer" if isinstance(event, Answer) else "refusal"
            yield ServerSentEvent(event=kind, data={"conversation_id": asking.conversation_id, "turn": turn})
    except FAILURES as error:
        yield ServerSentEvent(event="error", data=failure(error))


if (WEB := DATA.parents[1] / "web" / "dist").is_dir():
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
