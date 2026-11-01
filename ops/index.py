import argparse
import asyncio
from datetime import date
from http import HTTPStatus
from typing import Any

import httpx
from agent_framework.foundry import FoundryEmbeddingClient
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import DefaultAzureCredential

from app.config import SharedBase
from app.corpus import Corpus

API_VERSION = "2026-04-01"
SEARCH_SCOPE = "https://search.azure.com/.default"
BATCH = 100
WAIT_POLLS = 80
TARGETS = {"local": "local", "staging": "stg", "production": "prod"}
AI_SERVICES = {"@odata.type": "#Microsoft.Azure.Search.AIServicesByIdentity", "identity": None}
PAGES = "/document/textItems/*"
SKILLS = {
    "Text.SplitSkill": ("/document", "text", "/document/content", "textItems"),
    "Text.AzureOpenAIEmbeddingSkill": (PAGES, "text", PAGES, "embedding"),
}
SPLIT = {"textSplitMode": "pages", "maximumPageLength": 2000, "pageOverlapLength": 500}
PROJECTED = {"content": PAGES, "content_vector": f"{PAGES}/embedding"}
SOFT_DELETE = {"@odata.type": "#Microsoft.Azure.Search.NativeBlobSoftDeleteDeletionDetectionPolicy"}


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


def index(name: str, settings: SharedBase) -> dict[str, Any]:
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


def enrichment(short: str, settings: SharedBase, storage_id: str) -> list[tuple[str, dict[str, Any]]]:
    model, account = settings.embedding_model, settings.foundry_account_endpoint
    embedding = {"resourceUri": account, "deploymentId": model, "modelName": model, "dimensions": 1536}
    options: list[dict[str, Any]] = [SPLIT, embedding]
    skills = [
        {"@odata.type": f"#Microsoft.Skills.{kind}", "context": context}
        | {"inputs": [{"name": i, "source": source}], "outputs": [{"name": output}]}
        | extra
        for (kind, (context, i, source, output)), extra in zip(SKILLS.items(), options, strict=True)
    ]
    target, corpus, skillset, indexer = (f"jur-{kind}-{short}" for kind in ("articles", "corpus", "layout", "indexer"))
    mappings = [{"name": name, "source": source} for name, source in PROJECTED.items()]
    selector = dict(targetIndexName=target, parentKeyFieldName="parent_id", sourceContext=PAGES, mappings=mappings)
    projections = {"selectors": [selector], "parameters": {"projectionMode": "skipIndexingParentDocuments"}}
    connection = {"connectionString": f"ResourceId={storage_id};"}
    source = dict(name=corpus, type="azureblob", container={"name": "corpus"}, credentials=connection)
    services = AI_SERVICES | {"subdomainUrl": account}
    text = {"configuration": {"dataToExtract": "contentAndMetadata"}}
    return [
        ("datasources", source | {"dataDeletionDetectionPolicy": SOFT_DELETE}),
        ("skillsets", dict(name=skillset, skills=skills, indexProjections=projections, cognitiveServices=services)),
        (
            "indexers",
            dict(name=indexer, dataSourceName=corpus, skillsetName=skillset, targetIndexName=target, parameters=text),
        ),
    ]


async def push(http: httpx.AsyncClient, name: str, settings: SharedBase, credential: AsyncTokenCredential) -> str:
    documents = articles(Corpus.load())
    embeddings = FoundryEmbeddingClient(
        project_endpoint=settings.foundry_project_endpoint, model=settings.embedding_model, credential=credential
    )
    for start in range(0, len(documents), BATCH):
        batch = documents[start : start + BATCH]
        vectors = await embeddings.get_embeddings([document["content"] for document in batch])
        for document, vector in zip(batch, vectors, strict=True):
            document["content_vector"] = vector.vector
        response = (await http.post(f"/indexes/{name}/docs/index", json={"value": batch})).raise_for_status()
        failed = [item["key"] for item in response.json()["value"] if not item["status"]]
        if failed:
            raise RuntimeError(f"{len(failed)} documents were not indexed, first {failed[0]}")
    return f"{len(documents)} documents"


async def crawl(http: httpx.AsyncClient, objects: list[tuple[str, dict[str, Any]]]) -> str:
    for collection, body in objects:
        response = await http.put(f"/{collection}/{body['name']}", json=body)
        if response.is_error:
            raise RuntimeError(f"{collection}/{body['name']}: {response.status_code} {response.text}")
    indexer = objects[-1][1]["name"]
    if (await http.post(f"/indexers/{indexer}/run")).status_code not in (HTTPStatus.ACCEPTED, HTTPStatus.CONFLICT):
        raise RuntimeError(f"{indexer} did not start")
    for _ in range(WAIT_POLLS):
        await asyncio.sleep(15)
        result = (await http.get(f"/indexers/{indexer}/status")).raise_for_status().json()["lastResult"] or {}
        if result.get("status") not in (None, "inProgress"):
            break
    if result.get("status") != "success" or result.get("itemsFailed"):
        raise RuntimeError(f"{indexer}: {result.get('status')}, {result.get('errorMessage') or result.get('errors')}")
    return f"{indexer}: {result['itemsProcessed']} parts processed, {result['itemsFailed']} failed"


async def build(target: str, settings: SharedBase, storage_id: str | None) -> str:
    short = TARGETS[target]
    name = f"jur-articles-{short}"
    async with DefaultAzureCredential() as credential:
        token = await credential.get_token(SEARCH_SCOPE)
        headers, params = {"Authorization": f"Bearer {token.token}"}, {"api-version": API_VERSION}
        async with httpx.AsyncClient(
            base_url=settings.search_endpoint, headers=headers, params=params, timeout=60
        ) as http:
            (await http.put(f"/indexes/{name}", json=index(name, settings))).raise_for_status()
            if target == "local":
                return f"{name}: {await push(http, name, settings, credential)}"
            return await crawl(http, enrichment(short, settings, storage_id or ""))


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Juriscope search index and fill it.")
    parser.add_argument("--target", choices=list(TARGETS), required=True)
    parser.add_argument("--storage-id", help="resource id of the environment's storage account (not for local)")
    args = parser.parse_args()
    print(asyncio.run(build(args.target, SharedBase(), args.storage_id)))


if __name__ == "__main__":
    main()
