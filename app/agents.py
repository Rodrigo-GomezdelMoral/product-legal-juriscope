from pathlib import Path
from typing import Any

from agent_framework import Agent, SupportsChatGetResponse
from agent_framework.foundry import FoundryChatClient
from azure.core.credentials_async import AsyncTokenCredential
from pydantic import BaseModel

from app.config import SharedBase
from app.models import ArticleVersion, Citation, Draft, LegalQuery

PROMPTS = Path(__file__).resolve().parent / "prompts"
ANALYST = (PROMPTS / "analyst_v3.md").read_text(encoding="utf-8")
COUNSEL = (PROMPTS / "counsel_v4.md").read_text(encoding="utf-8")
TIMEOUT_SECONDS = 60
EFFORT = "low"


def chat_client(settings: SharedBase, credential: AsyncTokenCredential) -> FoundryChatClient:
    client = FoundryChatClient(
        project_endpoint=settings.foundry_project_endpoint, model=settings.chat_model, credential=credential
    )
    client.client = client.client.with_options(timeout=TIMEOUT_SECONDS)
    return client


def options(response_format: type[BaseModel], max_tokens: int) -> dict[str, Any]:
    return {
        "response_format": response_format,
        "reasoning": {"effort": EFFORT},
        "max_tokens": max_tokens,
        "store": False,
    }


def analyst(client: SupportsChatGetResponse[Any]) -> Agent:
    return Agent(client, ANALYST, name="analyst", default_options=options(LegalQuery, 800))


def counsel(client: SupportsChatGetResponse[Any]) -> Agent:
    return Agent(client, COUNSEL, name="counsel", default_options=options(Draft, 3000))


def article(citation: Citation, version: ArticleVersion, label: str) -> str:
    return (
        f'<article id="{citation.block_id}" title="{citation.title}" version="{label}" in_force="{version.in_force}" '
        f'norm="{version.norm}">\n{version.text}\n</article>'
    )


def brief(query: LegalQuery, citations: list[Citation]) -> str:
    when = f"{query.facts_date}, versions in force on that date" if query.facts_date else "none"
    parts = [f"Question: {query.question}\nAnswer in: {query.language}\nDate of the facts: {when}"]
    for citation in citations:
        parts.append(article(citation, citation.version, "applicable"))
        parts += [article(citation, citation.current, "current")] if citation.current else []
    return "\n\n".join(parts)
