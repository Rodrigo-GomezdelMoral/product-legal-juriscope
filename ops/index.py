import argparse
import asyncio
from datetime import date
from typing import Any

import httpx
from agent_framework.foundry import FoundryEmbeddingClient
from azure.identity.aio import DefaultAzureCredential

from app.config import Settings
from app.corpus import Corpus

API_VERSION = "2026-04-01"
SEARCH_SCOPE = "https://search.azure.com/.default"
BATCH = 100


SEMANTIC = {
    "defaultConfiguration": "default",
    "configurations": [
        {
            "name": "default",
            "prioritizedFields": {
                "titleField": {"fieldName": "headings"},
                "prioritizedContentFields": [{"fieldName": "content"}],
            },
        }
    ],
}


def index(name: str, settings: Settings) -> dict[str, Any]:
    text = {"type": "Edm.String", "searchable": True, "analyzer": "es.microsoft"}
    vectorizer = {
        "resourceUri": settings.foundry_account_endpoint,
        "deploymentId": settings.embedding_model,
        "modelName": settings.embedding_model,
    }
    return {
        "name": name,
        "fields": [
            {"name": "chunk_id", "type": "Edm.String", "key": True, "analyzer": "keyword"},
            {"name": "parent_id", "type": "Edm.String", "filterable": True},
            {"name": "content", **text},
            {"name": "headings", **text},
            {"name": "content_vector", "type": "Collection(Edm.Single)", "searchable": True, "retrievable": False}
            | {"stored": False, "dimensions": 1536, "vectorSearchProfile": "int8-hnsw"},
        ],
        "vectorSearch": {
            "algorithms": [{"name": "hnsw", "kind": "hnsw"}],
            "compressions": [{"name": "int8", "kind": "scalarQuantization"}],
            "vectorizers": [{"name": "embeddings", "kind": "azureOpenAI", "azureOpenAIParameters": vectorizer}],
            "profiles": [{"name": "int8-hnsw", "algorithm": "hnsw", "compression": "int8", "vectorizer": "embeddings"}],
        },
        "semantic": SEMANTIC,
    }


def articles(corpus: Corpus) -> list[dict[str, Any]]:
    today = date.today()
    return [
        {
            "@search.action": "upload",
            "chunk_id": b,
            "parent_id": b,
            "headings": a.title,
            "content": f"{a.title}\n{v.text}",
        }
        for b, a in corpus.articles.items()
        if (v := corpus.version_at(b, today))
    ]


async def push_local(settings: Settings) -> int:
    name, documents = "jur-articles-local", articles(Corpus.load())
    async with DefaultAzureCredential() as credential:
        token = await credential.get_token(SEARCH_SCOPE)
        embeddings = FoundryEmbeddingClient(
            project_endpoint=settings.foundry_project_endpoint, model=settings.embedding_model, credential=credential
        )
        headers, params = {"Authorization": f"Bearer {token.token}"}, {"api-version": API_VERSION}
        async with httpx.AsyncClient(
            base_url=settings.search_endpoint, headers=headers, params=params, timeout=60
        ) as http:
            (await http.put(f"/indexes/{name}", json=index(name, settings))).raise_for_status()
            for start in range(0, len(documents), BATCH):
                batch = documents[start : start + BATCH]
                vectors = await embeddings.get_embeddings([document["content"] for document in batch])
                for document, vector in zip(batch, vectors, strict=True):
                    document["content_vector"] = vector.vector
                response = (await http.post(f"/indexes/{name}/docs/index", json={"value": batch})).raise_for_status()
                failed = [item["key"] for item in response.json()["value"] if not item["status"]]
                if failed:
                    raise RuntimeError(f"{len(failed)} documents were not indexed, first {failed[0]}")
    return len(documents)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Juriscope search index and fill it.")
    parser.add_argument("--target", choices=["local"], required=True)
    parser.parse_args()
    print(f"jur-articles-local: {asyncio.run(push_local(Settings()))} documents")


if __name__ == "__main__":
    main()
