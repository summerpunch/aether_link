from typing import TypeVar, Generic, Optional, Any, Union, Generator
from pydantic import BaseModel
from fastapi import status
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
    def success(cls, data: Any = None, message: str = "success") -> "JSONResponse":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=cls(code=ErrorCode.HTTP_200_OK.code,
                        timestamp=ApiResult.get_now_with_milliseconds(),
                        message=message,
                        data=data).model_dump()
        )

    @classmethod
    def fail(cls, code: Optional[int] = 5000, message: str = "error") -> "JSONResponse":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=cls(code=code,
                        timestamp=ApiResult.get_now_with_milliseconds(),
                        message=message).model_dump()
        )
