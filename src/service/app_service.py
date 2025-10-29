import json
import logging
import uuid
from typing import Any, Generator
from dotenv import load_dotenv

from src.core.exception.exception import NotFoundException, ForbiddenException, ValidateErrorException, FailException
from src.engine.agent.agents import FunctionCallAgent, ReACTAgent
from src.engine.agent.entities.agent_entity import AgentConfig
from src.engine.agent.entities.queue_entity import QueueEvent
from src.engine.conversation_entity import InvokeFrom
from src.engine.language_model.entities.model_entity import ModelFeature, ModelParameterType
from src.engine.memory import TokenBufferMemory
from src.engine.tools.builtin.provider_manager import BuiltinProviderManager
from src.enums.app_enum import AppStatus, AppConfigType, DEFAULT_APP_CONFIG
from src.enums.workflow_enum import MessageStatus, WorkflowStatus
from src.schema.app_schema import CreateAppReq, ChatReq
from src.service.language_model_service import LanguageModelService
from src.store.model import Message, App, AppConfigVersion, ApiTool, Workflow, Conversation
from injector import inject
from src.lib.helper import get_value_type
from src.service.base_service import BaseService
from dataclasses import dataclass
from src.store.database_manager import DatabaseManager
from src.service.app_config_service import AppConfigService
from src.service.chat_service import ChatService

load_dotenv()

logger = logging.getLogger(__name__)


@inject
@dataclass
class AppService(BaseService):
    database_manager: DatabaseManager
    app_config_service: AppConfigService
    language_model_service: LanguageModelService
    chat_service: ChatService
    builtin_provider_manager: BuiltinProviderManager

    def chat(self, req: ChatReq, account: str) -> Generator:
        """根据传递的应用id+提问query向特定的应用发起会话调试"""
        # 1.获取应用信息并校验权限

        app = self.get_app(req.app_id, account)

        # 2.获取应用的最新草稿配置信息
        draft_app_config = self.app_config_service.get_draft_app_config(req.app_id)

        # 3.获取当前应用的调试会话信息

        conversation_id = None
        debug_conversation = None
        if app.debug_conversation_id is not None:
            debug_conversation = self.database_manager.session.query(Conversation).filter(
                Conversation.id == app.debug_conversation_id,
                Conversation.invoke_from == InvokeFrom.DEBUGGER,
            ).one_or_none()
            conversation_id = debug_conversation.id

        # 2.检测数据是否存在，如果不存在则创建
        if not app.debug_conversation_id or not debug_conversation:
            debug_conversation = Conversation(
                app_id=app.id,
                name="New Conversation",
                invoke_from=InvokeFrom.DEBUGGER,
                created_by=account,
            )
            debug_conversation = self.create(Conversation, **{**debug_conversation.to_dict()})
            conversation_id = debug_conversation.id
            self.update_by_filter(
                model=App,
                filters={
                    "id": f"{app.id}",
                },
                update_fields={
                    "debug_conversation_id": conversation_id
                }
            )

        # 4.新建一条消息记录
        message = self.create(
            Message,
            app_id=req.app_id,
            conversation_id=conversation_id,
            invoke_from=InvokeFrom.DEBUGGER,
            created_by=account,
            query=req.query,
            image_urls=req.image_urls,
            status=MessageStatus.NORMAL,
        )

        # 5.从语言模型管理器中加载大语言模型
        llm = self.language_model_service.load_language_model(draft_app_config.get("model_config", {}))

        # 6.实例化TokenBufferMemory用于提取短期记忆
        token_buffer_memory = TokenBufferMemory(
            database_manager=self.database_manager,
            conversation_id=conversation_id,
            model_instance=llm,
        )
        history = token_buffer_memory.get_history_prompt_messages(
            message_limit=draft_app_config["dialog_round"],
        )

        # 7.将草稿配置中的tools转换成LangChain工具
        tools = self.app_config_service.get_langchain_tools_by_tools_config(draft_app_config["tools"])

        # 10.检测是否关联工作流，如果关联了工作流则将工作流构建成工具添加到tools中
        if draft_app_config["workflows"]:
            workflow_tools = self.app_config_service.get_langchain_tools_by_workflow_ids(
                [workflow["id"] for workflow in draft_app_config["workflows"]]
            )
            tools.extend(workflow_tools)

        # 10.根据LLM是否支持tool_call决定使用不同的Agent
        agent_class = FunctionCallAgent if ModelFeature.TOOL_CALL in llm.features else ReACTAgent
        agent = agent_class(
            llm=llm,
            agent_config=AgentConfig(
                user_id=account,
                invoke_from=InvokeFrom.DEBUGGER,
                preset_prompt=draft_app_config["preset_prompt"],
                enable_long_term_memory=draft_app_config["long_term_memory"]["enable"],
                tools=tools,
                review_config=draft_app_config["review_config"],
            ),
        )

        agent_thoughts = {}
        for agent_thought in agent.stream({
            "messages": [llm.convert_to_human_message(req.query, req.image_urls)],
            "history": history
            # "long_term_memory": debug_conversation.summary,
        }):
            # 11.提取thought以及answer
            event_id = str(agent_thought.id)

            # 12.将数据填充到agent_thought，便于存储到数据库服务中
            if agent_thought.event != QueueEvent.PING:
                # 13.除了agent_message数据为叠加，其他均为覆盖
                if agent_thought.event == QueueEvent.AGENT_MESSAGE:
                    if event_id not in agent_thoughts:
                        # 14.初始化智能体消息事件
                        agent_thoughts[event_id] = agent_thought
                    else:
                        # 15.叠加智能体消息
                        agent_thoughts[event_id] = agent_thoughts[event_id].model_copy(update={
                            "thought": agent_thoughts[event_id].thought + agent_thought.thought,
                            # 消息相关数据
                            "message": agent_thought.message,
                            "message_token_count": agent_thought.message_token_count,
                            "message_unit_price": agent_thought.message_unit_price,
                            "message_price_unit": agent_thought.message_price_unit,
                            # 答案相关数据
                            "answer": agent_thoughts[event_id].answer + agent_thought.answer,
                            "answer_token_count": agent_thought.answer_token_count,
                            "answer_unit_price": agent_thought.answer_unit_price,
                            "answer_price_unit": agent_thought.answer_price_unit,
                            # Agent推理统计相关
                            "total_token_count": agent_thought.total_token_count,
                            "total_price": agent_thought.total_price,
                            "latency": agent_thought.latency,
                        })
                else:
                    # 16.处理其他类型事件的消息
                    agent_thoughts[event_id] = agent_thought
            data = {
                **agent_thought.model_dump(include={
                    "event", "thought", "observation", "tool", "tool_input", "answer",
                    "total_token_count", "total_price", "latency",
                }),
                "id": event_id,
                "conversation_id": str("111"),
                "message_id": str(message.id),
                "task_id": str(agent_thought.task_id),
            }
            print(data)
            yield f"event: {agent_thought.event}\ndata:{json.dumps(data)}\n\n"

        # 22.将消息以及推理过程添加到数据库
        self.chat_service.save_agent_thoughts(
            account_id=account,
            app_id=app.id,
            app_config=draft_app_config,
            conversation_id=conversation_id,
            message_id=message.id,
            agent_thoughts=[agent_thought for agent_thought in agent_thoughts.values()],
        )

    async def create_app(self, req: CreateAppReq, account: str) -> App:
        """创建Agent应用服务"""
        app_id = str(uuid.uuid4())
        app_config_id = str(uuid.uuid4())
        app = App(
            id=app_id,
            account_id=account,
            name=req.name,
            icon=req.icon,
            draft_app_config_id=app_config_id,
            description=req.description,
            status=AppStatus.DRAFT,
        )
        app_version = AppConfigVersion(
            id=app_config_id,
            app_id=app_id,
            version=0,
            config_type=AppConfigType.DRAFT,
            **DEFAULT_APP_CONFIG,
        )
        self.create(App, **{**app.to_dict()})
        self.create(AppConfigVersion, **{**app_version.to_dict()})
        return app

    async def update_draft_app_config(
            self,
            app_id: str,
            draft_app_config: dict[str, Any],
            account: str,
    ) -> AppConfigVersion:
        """根据传递的应用id+草稿配置修改指定应用的最新草稿"""
        draft_app_config = self._validate_draft_app_config(draft_app_config, account)
        with self.database_manager.auto_commit():
            draft_app_config_record = self.database_manager.session.query(AppConfigVersion).filter(
                AppConfigVersion.app_id == app_id,
                AppConfigVersion.config_type == AppConfigType.DRAFT,
            ).one_or_none()
            if not draft_app_config_record:
                logger.info(f"未找到应用 {app_id} 的草稿配置，创建新的")
                draft_app_config_record = AppConfigVersion(
                    app_id=app_id,
                    version=0,
                    config_type=AppConfigType.DRAFT,
                    **DEFAULT_APP_CONFIG
                )
                self.database_manager.session.add(draft_app_config_record)
                self.database_manager.session.flush()
            else:
                logger.info(f"找到应用 {app_id} 的草稿配置，ID: {draft_app_config_record.id}")
            # 更新字段
            for field, value in draft_app_config.items():
                if hasattr(draft_app_config_record, field):
                    setattr(draft_app_config_record, field, value)
                else:
                    raise FailException(f"字段 {field} 不存在")
        return draft_app_config_record

    def _validate_draft_app_config(self, draft_app_config: dict[str, Any], account: str) -> dict[str, Any]:
        """校验传递的应用草稿配置信息，返回校验后的数据"""
        # 1.校验上传的草稿配置中对应的字段，至少拥有一个可以更新的配置
        acceptable_fields = [
            "model_config", "dialog_round", "preset_prompt",
            "tools", "workflows", "datasets", "retrieval_config",
            "long_term_memory", "opening_statement", "opening_questions",
            "speech_to_text", "text_to_speech", "suggested_after_answer", "review_config",
        ]

        # 2.判断传递的草稿配置是否在可接受字段内
        if (
                not draft_app_config
                or not isinstance(draft_app_config, dict)
                or set(draft_app_config.keys()) - set(acceptable_fields)
        ):
            raise ValidateErrorException("草稿配置字段出错，请核实后重试")

        # 3.校验model_config字段，provider/model使用严格校验(出错的时候直接抛出)，parameters使用宽松校验，出错时使用默认值
        if "model_config" in draft_app_config:
            # 3.1 获取模型配置并判断数据是否为字典
            model_config = draft_app_config["model_config"]
            if not isinstance(model_config, dict):
                raise ValidateErrorException("模型配置格式错误，请核实后重试")

            # 3.2 判断model_config键信息是否正确
            if set(model_config.keys()) != {"provider", "model", "parameters"}:
                raise ValidateErrorException("模型键配置格式错误，请核实后重试")

            # 3.3 判断模型提供者信息是否正确
            if not model_config["provider"] or not isinstance(model_config["provider"], str):
                raise ValidateErrorException("模型服务提供商类型必须为字符串")
            provider = self.language_model_manager.get_provider(model_config["provider"])
            if not provider:
                raise ValidateErrorException("该模型服务提供商不存在，请核实后重试")

            # 3.4 判断模型信息是否正确
            if not model_config["model"] or not isinstance(model_config["model"], str):
                raise ValidateErrorException("模型名字必须是否字符串")
            model_entity = provider.get_model_entity(model_config["model"])
            if not model_entity:
                raise ValidateErrorException("该服务提供商下不存在该模型，请核实后重试")

            # 3.5 判断传递的parameters是否正确，如果不正确则设置默认值，并剔除多余字段，补全未传递的字段
            parameters = {}
            for parameter in model_entity.parameters:
                # 3.6 从model_config中获取参数值，如果不存在则设置为默认值
                parameter_value = model_config["parameters"].get(parameter.name, parameter.default)

                # 3.7 判断参数是否必填
                if parameter.required:
                    # 3.8 参数必填，则值不允许为None，如果为None则设置默认值
                    if parameter_value is None:
                        parameter_value = parameter.default
                    else:
                        # 3.9 值非空则校验数据类型是否正确，不正确则设置默认值
                        if get_value_type(parameter_value) != parameter.type.value:
                            parameter_value = parameter.default
                else:
                    # 3.10 参数非必填，数据非空的情况下需要校验
                    if parameter_value is not None:
                        if get_value_type(parameter_value) != parameter.type.value:
                            parameter_value = parameter.default

                # 3.11 判断参数是否存在options，如果存在则数值必须在options中选择
                if parameter.options and parameter_value not in parameter.options:
                    parameter_value = parameter.default

                # 3.12 参数类型为int/float，如果存在min/max时候需要校验
                if parameter.type in [ModelParameterType.INT, ModelParameterType.FLOAT] and parameter_value is not None:
                    # 3.13 校验数值的min/max
                    if (
                            (parameter.min and parameter_value < parameter.min)
                            or (parameter.max and parameter_value > parameter.max)
                    ):
                        parameter_value = parameter.default

                parameters[parameter.name] = parameter_value

            # 3.13 覆盖Agent配置中的模型配置
            model_config["parameters"] = parameters
            draft_app_config["model_config"] = model_config

        # 4.校验dialog_round上下文轮数，校验数据类型以及范围
        if "dialog_round" in draft_app_config:
            dialog_round = draft_app_config["dialog_round"]
            if not isinstance(dialog_round, int) or not (0 <= dialog_round <= 100):
                raise ValidateErrorException("携带上下文轮数范围为0-100")

        # 5.校验preset_prompt
        if "preset_prompt" in draft_app_config:
            preset_prompt = draft_app_config["preset_prompt"]
            if not isinstance(preset_prompt, str) or len(preset_prompt) > 2000:
                raise ValidateErrorException("人设与回复逻辑必须是字符串，长度在0-2000个字符")

        # 6.校验tools工具
        if "tools" in draft_app_config:
            tools = draft_app_config["tools"]
            validate_tools = []

            # 6.1 tools类型必须为列表，空列表则代表不绑定任何工具
            if not isinstance(tools, list):
                raise ValidateErrorException("工具列表必须是列表型数据")
            # 6.2 tools的长度不能超过5
            if len(tools) > 5:
                raise ValidateErrorException("Agent绑定的工具数不能超过5")
            # 6.3 循环校验工具里的每一个参数
            for tool in tools:
                # 6.4 校验tool非空并且类型为字典
                if not tool or not isinstance(tool, dict):
                    raise ValidateErrorException("绑定插件工具参数出错")
                # 6.5 校验工具的参数是不是type、provider_id、tool_id、params
                if set(tool.keys()) != {"type", "provider_id", "tool_id", "params"}:
                    raise ValidateErrorException("绑定插件工具参数出错")
                # 6.6 校验type类型是否为builtin_tool以及api_tool
                if tool["type"] not in ["builtin_tool", "api_tool"]:
                    raise ValidateErrorException("绑定插件工具参数出错")
                # 6.7 校验provider_id和tool_id
                if (
                        not tool["provider_id"]
                        or not tool["tool_id"]
                        or not isinstance(tool["provider_id"], str)
                        or not isinstance(tool["tool_id"], str)
                ):
                    raise ValidateErrorException("插件提供者或者插件标识参数出错")
                # 6.8 校验params参数，类型为字典
                if not isinstance(tool["params"], dict):
                    raise ValidateErrorException("插件自定义参数格式错误")
                # 6.9 校验对应的工具是否存在，而且需要划分成builtin_tool和api_tool
                if tool["type"] == "builtin_tool":
                    builtin_tool = self.builtin_provider_manager.get_tool(tool["provider_id"], tool["tool_id"])
                    if not builtin_tool:
                        continue
                else:
                    api_tool = self.database_manager.session.query(ApiTool).filter(
                        ApiTool.provider_id == tool["provider_id"],
                        ApiTool.name == tool["tool_id"],
                        ApiTool.account_id == account,
                    ).one_or_none()
                    if not api_tool:
                        continue

                validate_tools.append(tool)

            # 6.10 校验绑定的工具是否重复
            check_tools = [f"{tool['provider_id']}_{tool['tool_id']}" for tool in validate_tools]
            if len(set(check_tools)) != len(validate_tools):
                raise ValidateErrorException("绑定插件存在重复")

            # 6.11 重新赋值工具
            draft_app_config["tools"] = validate_tools

        # 7.校验workflow，提取已发布+权限正确的工作流列表进行绑定（更新配置阶段不校验工作流是否可以正常运行）
        if "workflows" in draft_app_config:
            workflows = draft_app_config["workflows"]

            # 7.1 判断workflows是否为列表
            if not isinstance(workflows, list):
                raise ValidateErrorException("绑定工作流列表参数格式错误")
            # 7.2 判断关联的工作流列表是否超过5个
            if len(workflows) > 5:
                raise ValidateErrorException("Agent绑定的工作流数量不能超过5个")
            # 7.3 循环校验工作流的每个参数，类型必须为UUID
            # for workflow_id in workflows:
            #     try:
            #         UUID(workflow_id)
            #     except Exception as _:
            #         raise ValidateErrorException("工作流参数必须是UUID")
            # 7.4 判断是否重复关联了工作流
            if len(set(workflows)) != len(workflows):
                raise ValidateErrorException("绑定工作流存在重复")
            # 7.5 校验关联工作流的权限，剔除不属于当前账号，亦或者未发布的工作流
            workflow_records = self.database_manager.session.query(Workflow).filter(
                Workflow.id.in_(workflows),
                Workflow.account_id == account,
                Workflow.status == WorkflowStatus.PUBLISHED,
            ).all()
            workflow_sets = set([str(workflow_record.id) for workflow_record in workflow_records])
            draft_app_config["workflows"] = [workflow_id for workflow_id in workflows if workflow_id in workflow_sets]

        # 8.校验datasets知识库列表
        # if "datasets" in draft_app_config:
        #     datasets = draft_app_config["datasets"]
        #
        #     # 8.1 判断datasets类型是否为列表
        #     if not isinstance(datasets, list):
        #         raise ValidateErrorException("绑定知识库列表参数格式错误")
        #     # 8.2 判断关联的知识库列表是否超过5个
        #     if len(datasets) > 5:
        #         raise ValidateErrorException("Agent绑定的知识库数量不能超过5个")
        #     # 8.3 循环校验知识库的每个参数
        #     for dataset_id in datasets:
        #         try:
        #             UUID(dataset_id)
        #         except Exception as e:
        #             raise ValidateErrorException("知识库列表参数必须是UUID")
        #     # 8.4 判断是否传递了重复的知识库
        #     if len(set(datasets)) != len(datasets):
        #         raise ValidateErrorException("绑定知识库存在重复")
        #     # 8.5 校验绑定的知识库权限，剔除不属于当前账号的知识库
        #     dataset_records = self.db.session.query(Dataset).filter(
        #         Dataset.id.in_(datasets),
        #         Dataset.account_id == account.id,
        #     ).all()
        #     dataset_sets = set([str(dataset_record.id) for dataset_record in dataset_records])
        #     draft_app_config["datasets"] = [dataset_id for dataset_id in datasets if dataset_id in dataset_sets]

        # 9.校验retrieval_config检索配置
        if "retrieval_config" in draft_app_config:
            retrieval_config = draft_app_config["retrieval_config"]

            # 9.1 判断检索配置非空且类型为字典
            if not retrieval_config or not isinstance(retrieval_config, dict):
                raise ValidateErrorException("检索配置格式错误")
            # 9.2 校验检索配置的字段类型
            if set(retrieval_config.keys()) != {"retrieval_strategy", "k", "score"}:
                raise ValidateErrorException("检索配置格式错误")
            # 9.3 校验检索策略是否正确
            if retrieval_config["retrieval_strategy"] not in ["semantic", "full_text", "hybrid"]:
                raise ValidateErrorException("检测策略格式错误")
            # 9.4 校验最大召回数量
            if not isinstance(retrieval_config["k"], int) or not (0 <= retrieval_config["k"] <= 10):
                raise ValidateErrorException("最大召回数量范围为0-10")
            # 9.5 校验得分/最小匹配度
            if not isinstance(retrieval_config["score"], float) or not (0 <= retrieval_config["score"] <= 1):
                raise ValidateErrorException("最小匹配范围为0-1")

        # 10.校验long_term_memory长期记忆配置
        if "long_term_memory" in draft_app_config:
            long_term_memory = draft_app_config["long_term_memory"]

            # 10.1 校验长期记忆格式
            if not long_term_memory or not isinstance(long_term_memory, dict):
                raise ValidateErrorException("长期记忆设置格式错误")
            # 10.2 校验长期记忆属性
            if (
                    set(long_term_memory.keys()) != {"enable"}
                    or not isinstance(long_term_memory["enable"], bool)
            ):
                raise ValidateErrorException("长期记忆设置格式错误")

        # 11.校验opening_statement对话开场白
        if "opening_statement" in draft_app_config:
            opening_statement = draft_app_config["opening_statement"]

            # 11.1 校验对话开场白类型以及长度
            if not isinstance(opening_statement, str) or len(opening_statement) > 2000:
                raise ValidateErrorException("对话开场白的长度范围是0-2000")

        # 12.校验opening_questions开场建议问题列表
        if "opening_questions" in draft_app_config:
            opening_questions = draft_app_config["opening_questions"]

            # 12.1 校验是否为列表，并且长度不超过3
            if not isinstance(opening_questions, list) or len(opening_questions) > 3:
                raise ValidateErrorException("开场建议问题不能超过3个")
            # 12.2 开场建议问题每个元素都是一个字符串
            for opening_question in opening_questions:
                if not isinstance(opening_question, str):
                    raise ValidateErrorException("开场建议问题必须是字符串")

        # 13.校验speech_to_text语音转文本
        if "speech_to_text" in draft_app_config:
            speech_to_text = draft_app_config["speech_to_text"]

            # 13.1 校验语音转文本格式
            if not speech_to_text or not isinstance(speech_to_text, dict):
                raise ValidateErrorException("语音转文本设置格式错误")
            # 13.2 校验语音转文本属性
            if (
                    set(speech_to_text.keys()) != {"enable"}
                    or not isinstance(speech_to_text["enable"], bool)
            ):
                raise ValidateErrorException("语音转文本设置格式错误")

        # 14.校验text_to_speech文本转语音设置
        # if "text_to_speech" in draft_app_config:
        #     text_to_speech = draft_app_config["text_to_speech"]
        #
        #     # 14.1 校验字典格式
        #     if not isinstance(text_to_speech, dict):
        #         raise ValidateErrorException("文本转语音设置格式错误")
        #     # 14.2 校验字段类型
        #     if (
        #             set(text_to_speech.keys()) != {"enable", "voice", "auto_play"}
        #             or not isinstance(text_to_speech["enable"], bool)
        #             or text_to_speech["voice"] not in ALLOWED_AUDIO_VOICES
        #             or not isinstance(text_to_speech["auto_play"], bool)
        #     ):
        #         raise ValidateErrorException("文本转语音设置格式错误")

        # 15.校验回答后生成建议问题
        if "suggested_after_answer" in draft_app_config:
            suggested_after_answer = draft_app_config["suggested_after_answer"]

            # 10.1 校验回答后建议问题格式
            if not suggested_after_answer or not isinstance(suggested_after_answer, dict):
                raise ValidateErrorException("回答后建议问题设置格式错误")
            # 10.2 校验回答后建议问题格式
            if (
                    set(suggested_after_answer.keys()) != {"enable"}
                    or not isinstance(suggested_after_answer["enable"], bool)
            ):
                raise ValidateErrorException("回答后建议问题设置格式错误")

        # 16.校验review_config审核配置
        if "review_config" in draft_app_config:
            review_config = draft_app_config["review_config"]

            # 16.1 校验字段格式，非空
            if not review_config or not isinstance(review_config, dict):
                raise ValidateErrorException("审核配置格式错误")
            # 16.2 校验字段信息
            if set(review_config.keys()) != {"enable", "keywords", "inputs_config", "outputs_config"}:
                raise ValidateErrorException("审核配置格式错误")
            # 16.3 校验enable
            if not isinstance(review_config["enable"], bool):
                raise ValidateErrorException("review.enable格式错误")
            # 16.4 校验keywords
            if (
                    not isinstance(review_config["keywords"], list)
                    or (review_config["enable"] and len(review_config["keywords"]) == 0)
                    or len(review_config["keywords"]) > 100
            ):
                raise ValidateErrorException("review.keywords非空且不能超过100个关键词")
            for keyword in review_config["keywords"]:
                if not isinstance(keyword, str):
                    raise ValidateErrorException("review.keywords敏感词必须是字符串")
            # 16.5 校验inputs_config输入配置
            if (
                    not review_config["inputs_config"]
                    or not isinstance(review_config["inputs_config"], dict)
                    or set(review_config["inputs_config"].keys()) != {"enable", "preset_response"}
                    or not isinstance(review_config["inputs_config"]["enable"], bool)
                    or not isinstance(review_config["inputs_config"]["preset_response"], str)
            ):
                raise ValidateErrorException("review.inputs_config必须是一个字典")
            # 16.6 校验outputs_config输出配置
            if (
                    not review_config["outputs_config"]
                    or not isinstance(review_config["outputs_config"], dict)
                    or set(review_config["outputs_config"].keys()) != {"enable"}
                    or not isinstance(review_config["outputs_config"]["enable"], bool)
            ):
                raise ValidateErrorException("review.outputs_config格式错误")
            # 16.7 在开启审核模块的时候，必须确保inputs_config或者是outputs_config至少有一个是开启的
            if review_config["enable"]:
                if (
                        review_config["inputs_config"]["enable"] is False
                        and review_config["outputs_config"]["enable"] is False
                ):
                    raise ValidateErrorException("输入审核和输出审核至少需要开启一项")

                if (
                        review_config["inputs_config"]["enable"]
                        and review_config["inputs_config"]["preset_response"].strip() == ""
                ):
                    raise ValidateErrorException("输入审核预设响应不能为空")

        return draft_app_config

    def get_app(self, app_id: str, account: str) -> App:
        """根据传递的id获取应用的基础信息"""
        # 1.查询数据库获取应用基础信息
        app = self.get(App, app_id)

        # 2.判断应用是否存在
        if not app:
            raise NotFoundException("该应用不存在，请核实后重试")

        # 3.判断当前账号是否有权限访问该应用
        if app.account_id != account:
            raise ForbiddenException("当前账号无权限访问该应用，请核实后尝试")

        return app

    # def get_draft_app_config(self, app_id: str) -> dict[str, Any]:
    #     """根据传递的应用id，获取指定的应用草稿配置信息"""
    #     app = self.get_app(app_id)
    #     return self.app_config_service.get_draft_app_config(app)
