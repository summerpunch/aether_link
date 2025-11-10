from dataclasses import dataclass
from src.utils import helper_util
from injector import inject
from src.service.base_service import BaseService
from src.store.database_manager import DatabaseManager
from src.store.model import Conversation, AgentRun


@inject
@dataclass
class ConversationService(BaseService):
    database_manager: DatabaseManager

    async def create_agent_run_id(self,
                                  thread_id: str,
                                  account: str):
        now = helper_util.create_datetime()
        _id = helper_util.generate_business_id()
        self.create(AgentRun, **{
            "id": _id,
            "conversation_id": thread_id,
            "created_at": now,
            "updated_at": now,
            "created_by": account,
        })
        return _id

    async def create_conversation(
            self,
            app_id: str,
            account: str,
    ):
        now = helper_util.create_datetime()
        _id = helper_util.generate_business_id()
        self.create(Conversation, **{
            "id": _id,
            "app_id": app_id,
            "created_by": account,
            "created_at": now,
            "updated_at": now
        })
        return _id
