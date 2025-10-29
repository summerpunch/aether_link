from typing import Optional, Dict
from dataclasses import dataclass
import httpx
import logging
from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from src.core.singleton import singleton
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentConfig:
    model: Optional[str] = None
    temperature: Optional[float] = 0.0
    base_url: Optional[str] = None
    api_key: Optional[str] = None

    def get_model(self):
        if self.model is None:
            return os.getenv("LLM_BASE_MODEL")
        return self.model

    def get_base_url(self):
        if self.base_url is None:
            return os.getenv("LLM_BASE_URL")
        return self.base_url

    def get_api_key(self):
        if self.api_key is None:
            return os.getenv("LLM_BASE_API_KEY")
        return self.api_key

    def get_temperature(self):
        if self.temperature is None:
            return float(os.getenv("LLM_BASE_TEMPERATURE", 0.0))
        return self.temperature


@singleton
class LLMFactory:

    def __init__(self):
        self._llm_cache: Dict[str, BaseLanguageModel] = {}

    @staticmethod
    def get_cached_key(config: AgentConfig) -> str:
        return f"{config.get_base_url()}_{config.get_model()}_{config.get_temperature()}"

    def get_cached_llm(self, config: AgentConfig) -> Optional[BaseLanguageModel]:
        cache_key = self.get_cached_key(config)
        if cache_key in self._llm_cache:
            logger.info(f"使用缓存的 LLM: {cache_key}")
            return self._llm_cache[cache_key]
        return None

    def _cached_llm(self, config: AgentConfig, llm: BaseLanguageModel) -> None:
        cache_key = self.get_cached_key(config)
        self._llm_cache[cache_key] = llm
        logger.info(f"缓存 LLM: {cache_key}")

    @staticmethod
    def _is_claude_37_or_4(model_name: str) -> bool:
        name = model_name.lower()
        return (
                "claude-3-7" in name
                or "claude-4" in name
                or "claude-opus-4" in name
                or "claude-sonnet-4" in name
        )

    @staticmethod
    def _is_deepseek(model_name: str) -> bool:
        name = model_name.lower()
        return "deepseek" in name

    @staticmethod
    def _is_qwq(model_name: str) -> bool:
        name = model_name.lower()
        return any(key in name for key in ("qwq", "qvq"))

    @staticmethod
    def _is_qwen(model_name: str) -> bool:
        name = model_name.lower()
        return "qwen" in name

    def default_llm(self, config: Optional[AgentConfig] = None) -> BaseLanguageModel:
        if config is None:
            config = AgentConfig()
        model = config.get_model()
        base_url = config.get_base_url()
        api_key = config.get_api_key()
        temperature = config.get_temperature()
        return ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            reasoning_effort="high",
            http_client=httpx.Client(verify=False),
            http_async_client=httpx.AsyncClient(verify=False)
        )

    def factory(self, config: AgentConfig) -> BaseLanguageModel:
        cached_llm = self.get_cached_llm(config)
        if cached_llm:
            return cached_llm
        model = config.get_model()
        base_url = config.get_base_url()
        api_key = config.get_api_key()
        temperature = config.get_temperature()
        logger.info(f"创建 LLM: model={model}, base_url={base_url}, temperature={temperature}")
        if self._is_claude_37_or_4(model):
            llm = ChatOpenAI(
                model=model,
                base_url=base_url,
                api_key=api_key,
                temperature=temperature,
                reasoning_effort="high",
                http_client=httpx.Client(verify=False),
                http_async_client=httpx.AsyncClient(verify=False)
            )
        elif self._is_deepseek(model):
            llm = ChatDeepSeek(
                model=model,
                api_base=base_url,
                api_key=api_key,
                temperature=temperature,
                reasoning_effort="high",
                http_client=httpx.Client(verify=False),
                http_async_client=httpx.AsyncClient(verify=False)
            )
        else:
            llm = ChatOpenAI(
                model=model,
                base_url=base_url,
                api_key=api_key,
                temperature=temperature,
                http_client=httpx.Client(verify=False),
                http_async_client=httpx.AsyncClient(verify=False)
            )
        self._cached_llm(config, llm)
        return llm


llm_factory = LLMFactory()
