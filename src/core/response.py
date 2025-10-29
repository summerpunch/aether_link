from typing import TypeVar, Generic, Optional, Any, Union, Generator
from pydantic import BaseModel
from fastapi import status
from fastapi.responses import JSONResponse
from src.enums.error_codes import ErrorCode
from datetime import datetime
from fastapi.responses import JSONResponse, StreamingResponse, Response

T = TypeVar('T')


class ApiResult(BaseModel, Generic[T]):
    code: int = ErrorCode.HTTP_200_OK.code
    message: str = "success"
    timestamp: Optional[str] = None
    data: Optional[T] = None

    @staticmethod
    def get_now_with_milliseconds():
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S.") + f"{int(now.microsecond / 1000):03d}"

    @classmethod
    async def success(cls, data: Any = None, message: str = "success") -> "JSONResponse":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=cls(code=ErrorCode.HTTP_200_OK.code,
                        timestamp=ApiResult.get_now_with_milliseconds(),
                        message=message,
                        data=data).model_dump()
        )

    @classmethod
    async def error(cls, code: Optional[int] = 5000, message: str = "error") -> "JSONResponse":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=cls(code=code,
                        timestamp=ApiResult.get_now_with_milliseconds(),
                        message=message).model_dump()
        )

    @classmethod
    def compact_generate_response(cls, response: Union[Response, Generator]) -> Response:
        """统一合并处理块输出以及流式事件输出 (FastAPI版本)"""
        # 1️⃣ 如果是普通 Response（非流式）
        if isinstance(response, Response):
            # FastAPI 的 Response 对象可直接返回
            # 如果 response 是 dict 或自定义对象，可用 JSONResponse 包装
            if isinstance(response, dict):
                return JSONResponse(content=response)
            return response

        # 2️⃣ 如果是生成器（流式输出）
        def generate() -> Generator:
            yield from response

        # 3️⃣ 返回 StreamingResponse，media_type 对应 text/event-stream
        return StreamingResponse(
            generate(),
            status_code=200,
            media_type="text/event-stream",
        )
