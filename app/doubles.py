import re
from collections.abc import AsyncIterator, Awaitable, Mapping, Sequence
from functools import partial
from typing import Any

from agent_framework import BaseChatClient, ChatResponse, ChatResponseUpdate, Content, FinishReason, ResponseStream
from pydantic import BaseModel

from app.models import Claim, Draft, LegalQuery

ARTICLE_ID = re.compile(r'<article id="([^"]+)"')
Reply = BaseModel | Exception | str


def default(response_format: type[BaseModel], last: str) -> BaseModel:
    if response_format is LegalQuery:
        return LegalQuery(in_scope=True, scope_reason="", search_queries=[last], facts_date=None, language="es")
    ids = list(dict.fromkeys(ARTICLE_ID.findall(last)))[:2]
    return Draft(claims=[Claim(text=f"El artículo con id {i} es aplicable.", article_ids=[i]) for i in ids])


class ModelDouble(BaseChatClient):
    def __init__(self, replies: Mapping[type[BaseModel], Reply] | None = None) -> None:
        super().__init__()
        self.replies, self.calls = dict(replies or {}), list[tuple[type[BaseModel], list[Any]]]()

    def _inner_get_response(
        self, *, messages: Sequence[Any], stream: bool, options: Mapping[str, Any], **kwargs: Any
    ) -> Awaitable[ChatResponse] | ResponseStream[ChatResponseUpdate, ChatResponse]:
        response_format = options["response_format"]
        self.calls.append((response_format, list(messages)))
        reply = self.replies.get(response_format) or default(response_format, messages[-1].text)
        if isinstance(reply, Exception):
            raise reply
        text = [] if isinstance(reply, str) else [Content.from_text(reply.model_dump_json())]
        usage = Content.from_usage({"input_token_count": 1000, "output_token_count": 200})
        finish = FinishReason(reply if isinstance(reply, str) else "stop")

        async def updates() -> AsyncIterator[ChatResponseUpdate]:
            yield ChatResponseUpdate(role="assistant", contents=[*text, usage], finish_reason=finish)

        final = partial(ChatResponse.from_updates, output_format_type=response_format)
        result = ResponseStream(updates(), finalizer=final)
        return result if stream else result.get_final_response()
