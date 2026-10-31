from typing import Any

from azure.cosmos import PartitionKey
from azure.cosmos.aio import ContainerProxy, CosmosClient, DatabaseProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from app.models import Conversation, ConversationSummary, Turn

TTL_SECONDS = 90 * 24 * 3600
NEWEST_FIRST = "SELECT c.id, c.title, c.updated FROM c ORDER BY c.updated DESC"


class Conversations:
    def __init__(self, container: ContainerProxy) -> None:
        self.container = container

    async def ping(self) -> None:
        await self.container.read()

    async def summaries(self, user_id: str) -> list[ConversationSummary]:
        items = self.container.query_items(NEWEST_FIRST, partition_key=user_id)
        return [ConversationSummary.model_validate(item) async for item in items]

    async def get(self, user_id: str, conversation_id: str) -> Conversation | None:
        try:
            return Conversation.model_validate(await self.container.read_item(conversation_id, partition_key=user_id))
        except CosmosResourceNotFoundError:
            return None

    async def add(self, user_id: str, conversation_id: str, turn: Turn, title: str | None) -> None:
        saved: dict[str, Any] = turn.model_dump(mode="json")
        if title is None:
            appended = {"op": "add", "path": "/turns/-", "value": saved}
            updated = {"op": "set", "path": "/updated", "value": saved["asked"]}
            await self.container.patch_item(conversation_id, user_id, [appended, updated])
            return
        record = {"id": conversation_id, "user_id": user_id, "title": title, "turns": [saved]}
        await self.container.create_item(record | {"updated": saved["asked"]})

    async def delete(self, user_id: str, conversation_id: str) -> None:
        try:
            await self.container.delete_item(conversation_id, partition_key=user_id)
        except CosmosResourceNotFoundError:
            return


async def emulator(cosmos: CosmosClient, name: str) -> DatabaseProxy:
    database = await cosmos.create_database_if_not_exists(name)
    for container, key in (("history", "/session_id"), ("conversations", "/user_id")):
        await database.create_container_if_not_exists(container, PartitionKey(key), default_ttl=TTL_SECONDS)
    return database
