import logging
from dataclasses import dataclass

from src.enums.redis_key_list import RedisKeyList
from src.enums.workflow_enum import MessageType
from src.store.redis_store import redis_client
from src.utils import helper_util
from injector import inject
from src.service.base_service import BaseService
from src.store.database_manager import DatabaseManager
from src.store.model import Message

logger = logging.getLogger(__name__)


@inject
@dataclass
class MessageService(BaseService):
    database_manager: DatabaseManager

    async def after_agent(self, app_id: str, thread_id: str, agent_run_id: str):
        logger.info(f"after_agent app_id:{app_id}, thread_id : {thread_id}, agent_run_id: {agent_run_id}")
        values = await redis_client.lrange(RedisKeyList.CHAT_STREAM_STORE.builder_key(agent_run_id), 0, -1)
        if values:
            logger.info(f"after_agent values {len(values)}")
            insert_list = []
            now = helper_util.create_datetime()
            for value in values:
                insert_list.append(
                    Message(
                        app_id=app_id,
                        conversation_id=thread_id,
                        agent_run_id=agent_run_id,
                        message_type=MessageType.AI.value.name,
                        created_at=now,
                        content=value
                    )
                )
            with self.database_manager.auto_commit():
                self.database_manager.session.add_all(insert_list)
                self.database_manager.session.flush()
