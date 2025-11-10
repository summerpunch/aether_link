from typing import Optional, Dict, Any
import json
import uuid
from ag_ui.core import *
from src.enums.redis_key_list import RedisKeyList
from src.store.redis_store import redis_client

skip = [
    'call_model',
    'agent',
    'tools',
    'Prompt',
    'post_model_hook',
    'post_model_hook_router',
    'post_model_hook_func',
    'RunnableSequence',
    'ChatPromptTemplate',
    'should_continue',
    'ChatLiteLLMRouter',
    'StrOutputParser'
]


async def get_run_id(event: Dict[str, Any]) -> str:
    return await get_value("run_id", event)

async def get_value(key: str, event: Dict[str, Any]) -> str:
    return str(event.get(key, ""))


async def event_encoder(event: BaseEvent) -> str:
    return event.model_dump_json(by_alias=True, exclude_none=True)

async def get_last_subgraph_worker_node(agent_run_id: str):
    return await redis_client.get_value(RedisKeyList.CHAT_STREAM_SUBGRAPH.builder_key(agent_run_id))


async def execute_store(agent_run_id: str, event: BaseEvent, has_store: Optional[bool] = True):
    if has_store:
        await redis_client.rpush(RedisKeyList.CHAT_STREAM_STORE.builder_key(agent_run_id),
                                 await event_encoder(event))


async def execute(thread_id: str, agent_run_id: str, event: Dict[str, Any]) -> Optional[list[str]]:
    name = event.get("name", "")
    if name in skip:
        return None
    event_type = event.get("event", "")
    print(event)


if __name__ == "__main__":
    print(1)
