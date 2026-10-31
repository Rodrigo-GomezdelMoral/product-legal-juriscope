from collections.abc import Awaitable, Callable

from azure.core.credentials_async import AsyncTokenCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizableTextQuery
from pydantic import BaseModel

TOP = 10
CANDIDATES = 50
VECTOR = "content_vector"


class Chunk(BaseModel):
    chunk_id: str
    content: str
    score: float
    reranker_score: float | None


Retriever = Callable[[list[str]], Awaitable[list[Chunk]]]


class SearchRetriever:
    def __init__(self, endpoint: str, index: str, credential: AsyncTokenCredential) -> None:
        self.client = SearchClient(endpoint, index, credential, connection_timeout=5, read_timeout=20)

    async def search(self, queries: list[str]) -> list[Chunk]:
        vectors = [VectorizableTextQuery(text=q, k_nearest_neighbors=CANDIDATES, fields=VECTOR) for q in queries]
        results = await self.client.search(
            search_text=" ".join(queries),
            vector_queries=list(vectors),
            query_type="semantic",
            semantic_configuration_name="default",
            select=["chunk_id", "content"],
            top=TOP,
        )
        return [
            Chunk(
                chunk_id=r["chunk_id"],
                content=r["content"],
                score=r["@search.score"],
                reranker_score=r.get("@search.reranker_score"),
            )
            async for r in results
        ]

    async def close(self) -> None:
        await self.client.close()
