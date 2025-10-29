from typing import Optional, Any

from langchain_openai import ChatOpenAI

from src.engine.language_model.entities.model_entity import BaseLanguageModel


class Chat(ChatOpenAI, BaseLanguageModel):
    """OpenAI聊天模型基类"""

    def __init__(
            self,
            model: str = "gpt-3.5-turbo",
            base_url: Optional[str] = None,
            api_key: Optional[str] = None,
            **kwargs: Any
    ):
        """
        初始化OpenAI聊天模型

        Args:
            model: 模型名称
            base_url: API基础URL，如果不提供则使用默认值
            api_key: API密钥，如果不提供则使用环境变量
            **kwargs: 其他参数
        """
        # 构建ChatOpenAI的初始化参数
        openai_kwargs = {
            "model": model,
            **kwargs
        }

        # 如果提供了base_url，则设置
        openai_kwargs["base_url"] = "https://llm-guard.mininglamp.com/v1"

        # 如果提供了api_key，则设置
        openai_kwargs["api_key"] = "sk-D9Ct1QbqDNpsaYv6B7C8AbDaA2Ea4a338c0b1d5d95FfD3E6"

        # 调用父类初始化
        super().__init__(**openai_kwargs)
