from enum import Enum
from dataclasses import dataclass


@dataclass
class RedisKey:
    key: str


class RedisKeyList(Enum):
    CHAT_STREAM_SSE = RedisKey("chat::stream::sse")

    CHAT_STREAM_STORE = RedisKey("chat::stream::store")

    CHAT_STREAM_SUBGRAPH = RedisKey("chat::stream::subgraph")

    CHAT_STREAM_TEXT = RedisKey("chat::stream::text")

    CHAT_STREAM_TEXT_THINKING = RedisKey("chat::stream::text::thinking")

    CHAT_STREAM_TOOL_THINKING = RedisKey("chat::stream::tool::thinking")

    CHAT_STREAM_TOOLS_RESULT = RedisKey("chat::stream::tools::result")

    CHAT_LOCK_COMPLETION = RedisKey("chat::lock::completion")

    CHAT_INFO = RedisKey("chat::info")

    WORKER_NODE_FINAL_RESULT = RedisKey("worker::node::final::result")

    SCHEDULER_CROWD = RedisKey("scheduler::crowd")

    SCHEDULER_TAG_SCORE = RedisKey("scheduler::tag::score")

    INCR_SEQ_CROWD = RedisKey("incr::seq::crowd")

    SCHEDULER_MA_FLOW = RedisKey("scheduler::ma:flow")

    # 标记 on_tool_start 的首次/二次触发控制
    TOOL_COPILOT_SKIP = RedisKey("tool::copilot::skip")

    def get_value(self) -> str:
        return self.value.key

    def builder_key(self, *values: any) -> str:
        parts = [str(self.value.key)] + [str(v) for v in values]
        return "::".join(parts)


if __name__ == "__main__":
    print(RedisKeyList.CHAT_STREAM_SSE.builder_key("sss"))
