import logging
from typing import List
from src.store.redis_store import redis_client
from src.enums.redis_key_list import RedisKeyList

logger = logging.getLogger(__name__)

REDIS_STREAM_EXPIRE_SECONDS = 1 * 60 * 60 * 24 * 30


async def consume_ai_stream_messages(agent_run_id: str,
                                     last_message_id: str = "0-0",
                                     count: int = 50,
                                     block_ms: int = 0):
    """消费 Stream 消息

    Args:
        agent_run_id: agent_run_id
        last_message_id: 上次读取的 ID，默认从头开始（"0-0"）
        count: 最大读取数量
        block_ms: 阻塞读取时间（毫秒），0 表示非阻塞

    Returns:
        list[tuple]: [(stream_key, [(msg_id, {fields})])]
    """
    try:
        key = RedisKeyList.CHAT_STREAM_SSE.builder_key(agent_run_id)
        return await redis_client.redis.xread({key: last_message_id}, count=count, block=block_ms)
    except Exception as e:
        logger.error(f"Failed to consume agent_run_id {agent_run_id} stream messages: {e}")
        return []


async def load_event_sse(agent_run_id: str, stream_read_message_id: str):
    messages = await consume_ai_stream_messages(
        agent_run_id,
        last_message_id=stream_read_message_id,
        count=200,
        block_ms=1000 * 30 * 1
    )
    if messages:
        for stream, msgs in messages:
            for msg_id, fields in msgs:
                yield msg_id, fields


async def add_ai_stream_messages_batch(thread_id: str, messages: List[str]) -> List[str]:
    """批量添加消息到 Redis Stream

    Args:
        thread_id: 会话 ID
        messages: 消息列表

    Returns:
        List[str]: 添加后的消息 ID 列表
    """
    try:
        key = RedisKeyList.CHAT_STREAM_SSE.builder_key(thread_id)
        redis = redis_client.redis
        pipe = redis.pipeline()

        for message in messages:
            pipe.xadd(key, {"value": message})

        pipe.expire(key, REDIS_STREAM_EXPIRE_SECONDS)
        results = await pipe.execute()
        message_ids = results[:-1]
        return message_ids
    except Exception as e:
        logger.error(f"Failed to add_ai_stream_messages_batch: {e}")
        return []

async def add_ai_stream_message(thread_id: str, message: str):
    await add_ai_stream_messages_batch(thread_id, [message])
