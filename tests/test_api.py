import base64
import hashlib
import json
import logging
from collections.abc import AsyncIterator
from copy import deepcopy
from typing import Any, cast
from uuid import uuid4

import httpx2
import pytest
from agent_framework.exceptions import ChatClientException
from azure.core.exceptions import ServiceRequestError
from azure.cosmos.aio import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from fastapi.testclient import TestClient
from openai import APIConnectionError, APIError, RateLimitError
from pydantic import BaseModel

from app.auth import OBJECT_ID, ROLE
from app.conversations import Conversations
from app.corpus import Corpus
from app.doubles import ModelDouble, Reply
from app.main import Services, app
from app.models import Draft, LegalQuery
from app.retrieval import Chunk, Retriever, SearchUnavailableError
from app.workflow import Juriscope
from tests.test_workflow import DictHistory, claims, query

QUESTION = "¿Cuál es la pena del homicidio de mi cliente?"
ASKED = {"question": QUESTION}


def principal(user: str, *roles: str, name: str = "Ana Ruiz", entra: bool = False) -> dict[str, str]:
    claims = [("oid" if entra else OBJECT_ID, user), ("name", name), *(("roles", role) for role in roles)]
    role_typ = "http://schemas.microsoft.com/ws/2008/06/identity/claims/role" if entra else "roles"
    body = {"claims": [{"typ": t, "val": v} for t, v in claims], "name_typ": "name", "role_typ": role_typ}
    return {"X-MS-CLIENT-PRINCIPAL": base64.b64encode(json.dumps(body).encode()).decode()}


ANA, LUIS = principal("user-a", ROLE), principal("user-b", ROLE, name="Luis")


class Container:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], dict[str, Any]] = {}
        self.down = False

    async def read(self) -> None:
        if self.down:
            raise ServiceRequestError("unreachable")

    async def read_item(self, item: str, partition_key: str) -> dict[str, Any]:
        await self.read()
        if (partition_key, item) not in self.items:
            raise CosmosResourceNotFoundError(message="missing")
        return deepcopy(self.items[(partition_key, item)])

    async def create_item(self, body: dict[str, Any]) -> None:
        self.items[(body["user_id"], body["id"])] = body

    async def patch_item(self, item: str, partition_key: str, patch_operations: list[dict[str, Any]]) -> None:
        if (partition_key, item) not in self.items:
            raise CosmosResourceNotFoundError(message="missing")
        record = self.items[(partition_key, item)]
        for operation in patch_operations:
            if operation["path"] == "/turns/-":
                record["turns"].append(operation["value"])
            else:
                record[operation["path"].strip("/")] = operation["value"]

    def query_items(self, query: str, partition_key: str) -> AsyncIterator[dict[str, Any]]:
        return self.newest(partition_key)

    async def newest(self, user: str) -> AsyncIterator[dict[str, Any]]:
        mine = [record for (owner, _), record in self.items.items() if owner == user]
        for record in sorted(mine, key=lambda r: str(r["updated"]), reverse=True):
            yield {key: record[key] for key in ("id", "title", "updated")}

    async def delete_item(self, item: str, partition_key: str) -> None:
        if self.items.pop((partition_key, item), None) is None:
            raise CosmosResourceNotFoundError(message="missing")


class Api:
    def __init__(
        self, corpus: Corpus, replies: dict[type[BaseModel], Reply] | None = None, search: Retriever | None = None
    ) -> None:
        self.corpus, self.container, self.history = corpus, Container(), DictHistory()
        defaults: dict[type[BaseModel], Reply] = {LegalQuery: query(), Draft: claims(["a138"])}
        self.model = ModelDouble(defaults | (replies or {}))
        self.juriscope = Juriscope(self.model, search or self.search, corpus, self.history, "gpt-5-mini")
        store = Conversations(cast(ContainerProxy, self.container))
        app.state.services = Services(self.juriscope, store, self.clear, {"updated": "2026-04-09"})
        self.http = TestClient(app)

    async def search(self, queries: list[str]) -> list[Chunk]:
        found = [self.corpus.articles[b] for b in ("a138", "a142")]
        return [Chunk(chunk_id=a.block_id, content=a.versions[-1].text, score=1.0, reranker_score=3.0) for a in found]

    async def clear(self, session_id: str | None) -> None:
        self.history.sessions.pop(session_id or "", None)

    def ask(self, conversation: str = "new", headers: dict[str, str] = ANA) -> list[tuple[str, Any]]:
        response = self.http.post(f"/api/conversations/{conversation}/messages", json=ASKED, headers=headers)
        assert response.status_code == 200, response.text
        blocks = [dict(line.split(": ", 1) for line in b.splitlines()) for b in response.text.split("\n\n") if b]
        return [(block["event"], json.loads(block["data"])) for block in blocks]


def problem(response: httpx2.Response, status: int) -> dict[str, Any]:
    assert response.status_code == status and response.headers["content-type"] == "application/problem+json"
    body: dict[str, Any] = response.json()
    assert body["status"] == status and len(body["trace_id"]) == 32
    return body


def test_401(corpus: Corpus) -> None:
    api = Api(corpus)
    problem(api.http.get("/api/me"), 401)
    problem(api.http.get("/api/me", headers={"X-MS-CLIENT-PRINCIPAL": "not a principal"}), 401)
    assert api.http.get("/healthz").json() == {"status": "ok"}


def test_403(corpus: Corpus) -> None:
    api = Api(corpus)
    problem(api.http.get("/api/conversations", headers=principal("user-a", "Other.Role")), 403)
    assert api.http.get("/api/me", headers=principal("user-a", ROLE, entra=True)).json() == {
        "name": "Ana Ruiz",
        "initials": "AR",
    }
    problem(api.http.get("/api/conversations/not-an-id", headers=ANA), 422)
    assert api.http.get("/api/meta", headers=ANA).json()["updated"] == "2026-04-09"


def test_sse_order(corpus: Corpus) -> None:
    api = Api(corpus)
    *phases, (kind, final) = api.ask()
    steps = [(event, data["step"]) for event, data in phases]
    assert steps == [("phase", s) for s in ("analysing", "searching", "reading", "drafting", "verifying")]
    assert kind == "answer" and final["turn"]["outcome"]["citations"][0]["block_id"] == "a138"
    saved = api.http.get(f"/api/conversations/{final['conversation_id']}", headers=ANA).json()
    assert saved["title"] == QUESTION and saved["turns"] == [final["turn"]]
    refused = Api(corpus, {LegalQuery: query(scope="case_law", search_queries=[])}).ask()
    assert [event for event, _ in refused] == ["phase", "refusal"] and refused[-1][1]["turn"]["outcome"][
        "scope"
    ] == "case_law"


def test_resume(corpus: Corpus) -> None:
    api = Api(corpus)
    first = api.ask()[-1][1]["conversation_id"]
    second = api.ask()[-1][1]["conversation_id"]
    api.ask(first)
    assert [m.role for m in api.model.calls[-2][1]] == ["user", "assistant", "user"]
    listed = api.http.get("/api/conversations", headers=ANA).json()
    assert [c["id"] for c in listed] == [first, second]
    assert len(api.http.get(f"/api/conversations/{first}", headers=ANA).json()["turns"]) == 2


def test_delete(corpus: Corpus) -> None:
    api = Api(corpus)
    first, second = (api.ask()[-1][1]["conversation_id"] for _ in range(2))
    kept = api.ask(headers=LUIS)[-1][1]["conversation_id"]
    assert api.http.delete(f"/api/conversations/{first}", headers=ANA).status_code == 204
    problem(api.http.get(f"/api/conversations/{first}", headers=ANA), 404)
    problem(api.http.delete(f"/api/conversations/{first}", headers=ANA), 404)
    assert first not in api.history.sessions and second in api.history.sessions
    assert api.http.delete("/api/conversations", headers=ANA).status_code == 204
    assert api.http.get("/api/conversations", headers=ANA).json() == [] and list(api.history.sessions) == [kept]


def test_404_other_user(corpus: Corpus) -> None:
    api = Api(corpus)
    theirs = api.ask()[-1][1]["conversation_id"]
    path = f"/api/conversations/{theirs}"
    for response in (
        api.http.get(path, headers=LUIS),
        api.http.delete(path, headers=LUIS),
        api.http.post(f"{path}/messages", json=ASKED, headers=LUIS),
    ):
        problem(response, 404)
    assert theirs in api.history.sessions and len(api.http.get(path, headers=ANA).json()["turns"]) == 1


def test_feedback_event(corpus: Corpus, caplog: pytest.LogCaptureFixture) -> None:
    api = Api(corpus)
    with caplog.at_level(logging.INFO, logger="juriscope"):
        turn = api.ask()[-1][1]["turn"]["id"]
        for value in ("up", "down", "copy"):
            assert api.http.post("/api/feedback", json={"turn_id": turn, "value": value}, headers=ANA).is_success
    sent = [r.__dict__ for r in caplog.records if r.name == "juriscope"]
    assert [(e["microsoft.custom_event.name"], e.get("value", e.get("via"))) for e in sent] == [
        ("QuestionAsked", None),
        ("AnswerDelivered", None),
        ("FeedbackGiven", "up"),
        ("AnswerAccepted", "up"),
        ("FeedbackGiven", "down"),
        ("AnswerAccepted", "copy"),
    ]
    assert {(e["user_hash"], e["turn_id"]) for e in sent} == {(hashlib.sha256(b"user-a").hexdigest()[:16], turn)}
    assert (sent[1]["outcome"], sent[1]["claims"], sent[1]["dropped_claims"]) == ("answer", 1, 0)
    assert not [e for e in sent if "homicidio" in repr(e) or "cliente" in repr(e)]


def throttled(cause: Exception) -> ChatClientException:
    error = ChatClientException("service failed to complete the prompt")
    error.__cause__ = cause
    return error


def test_model_429_is_503(corpus: Corpus) -> None:
    request = httpx2.Request("POST", "https://example.org")
    limited = RateLimitError(
        "429", response=httpx2.Response(429, headers={"retry-after": "7"}, request=request), body=None
    )
    for cause, wait in ((limited, "7"), (APIError("rate limit", request, body=None), "20")):
        api = Api(corpus, {LegalQuery: throttled(cause)})
        response = api.http.post("/api/conversations/new/messages", json=ASKED, headers=ANA)
        assert problem(response, 503)["retry_after"] == int(wait) and response.headers["Retry-After"] == wait
        assert api.http.get("/api/conversations", headers=ANA).json() == []
    late = Api(corpus, {Draft: throttled(APIError("rate limit", request, body=None))}).ask()
    assert late[-1][0] == "error" and (late[-1][1]["status"], late[-1][1]["retry_after"]) == (503, 20)
    lost = Api(corpus, {LegalQuery: throttled(APIConnectionError(request=request))})
    body = problem(lost.http.post("/api/conversations/new/messages", json=ASKED, headers=ANA), 503)
    assert body["detail"].startswith("The language model is unavailable") and body["retry_after"] == 20


async def unavailable(queries: list[str]) -> list[Chunk]:
    raise SearchUnavailableError("search is down")


def test_dependency_down_is_503(corpus: Corpus) -> None:
    api = Api(corpus, search=unavailable)
    *_, (kind, body) = api.ask()
    assert kind == "error" and body["status"] == 503 and body["detail"].startswith("Search")
    api.container.down = True
    assert problem(api.http.get("/healthz"), 503)["detail"].startswith("Conversation storage")
    assert problem(api.http.get(f"/api/conversations/{uuid4().hex}", headers=ANA), 503)["retry_after"] == 20


def test_deleted_while_answering(corpus: Corpus) -> None:
    api = Api(corpus)
    conversation = api.ask()[-1][1]["conversation_id"]

    async def deleting(queries: list[str]) -> list[Chunk]:
        api.container.items.clear()
        await api.clear(conversation)
        return await api.search(queries)

    api.juriscope.search = deleting
    *_, (kind, body) = api.ask(conversation)
    assert (kind, body["status"]) == ("error", 404) and conversation not in api.history.sessions
