import json
import re
import logging
import uuid
from typing import Optional, Dict, Any
from ag_ui.core import (
    StepStartedEvent,
    StepFinishedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    ToolCallArgsEvent,
    ToolCallStartEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    EventType,
    BaseEvent)
from langchain_core.messages import ToolMessage

logger = logging.getLogger(__name__)

skip = ['LangGraph',
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
        'StrOutputParser']

UNICODE_PATTERN = re.compile(r'\\u[0-9a-fA-F]{4}')


async def unicode_decode(value: Any):
    if isinstance(value, dict):
        value = json.dumps(value, ensure_ascii=False)
    if isinstance(value, str):
        if UNICODE_PATTERN.search(value):
            return value.encode().decode("unicode_escape")
    return value


async def get_run_id(event: Dict[str, Any]) -> str:
    return await get_value("run_id", event)


async def get_value(key: str, event: Dict[str, Any]) -> str:
    return str(event.get(key, ""))


async def event_encoder(event: BaseEvent) -> str:
    return event.model_dump_json(by_alias=True, exclude_none=True)


async def execute(event: Dict[str, Any]) -> Optional[list[str]]:
    name = event.get("name", "")
    if name in skip:
        return None
    run_id = await get_run_id(event)
    event_type = event.get("event", "")
    metadata = event.get("metadata", {}).get("langgraph_node")
    match event_type:
        case "on_chain_start":
            if "start_" in metadata:
                ag_event = StepStartedEvent(
                    step_name=name
                )
                return [await event_encoder(ag_event)]
        case "on_chain_end":
            if "end_" in metadata:
                ag_event = StepFinishedEvent(
                    step_name=name
                )
                return [await event_encoder(ag_event)]
        case "on_chat_model_start":
            ag_event = TextMessageStartEvent(message_id=run_id)
            return [await event_encoder(ag_event)]
        case "on_chat_model_stream":
            content = event.get("data")["chunk"].content
            if content:
                ag_event = TextMessageContentEvent(message_id=run_id,
                                                   delta=content)
                return [await event_encoder(ag_event)]
        case "on_tool_end":
            return await on_tool_copilot(event)


async def on_tool_copilot(event: Dict[str, Any]) -> Optional[list[str]]:
    tool_call_id = str(uuid.uuid4())
    run_id = await get_run_id(event)
    tool_call_name = await get_value("name", event)
    input_value = event.get("data", {}).get("input")
    output_value = event.get("data", {}).get("output")

    if isinstance(output_value, ToolMessage):
        output_value = output_value.content

    tool_start_event = ToolCallStartEvent(
        tool_call_id=tool_call_id,
        tool_call_name=tool_call_name,
    )
    tool_args_event = ToolCallArgsEvent(
        tool_call_id=tool_call_id,
        delta=await unicode_decode(input_value)
    )
    tool_end_event = ToolCallEndEvent(
        tool_call_id=tool_call_id
    )
    tool_result_event = ToolCallResultEvent(
        tool_call_id=tool_call_id,
        message_id=run_id,
        content=await unicode_decode(output_value),
        type=EventType.TOOL_CALL_RESULT
    )
    return [
        await event_encoder(tool_start_event),
        await event_encoder(tool_args_event),
        await event_encoder(tool_end_event),
        await event_encoder(tool_result_event)
    ]
