from dataclasses import field
from typing import Any

from src.enums.http_code import HttpCode


class BusinessException(Exception):
    """基础自定义异常信息"""
    code: HttpCode = HttpCode.FAIL
    message: str = ""
    data: Any = field(default_factory=dict)

    def __init__(self, message: str = None, data: Any = None):
        super().__init__()
        self.message = message
        self.data = data


class FailException(BusinessException):
    """通用失败异常"""
    pass


class NotFoundException(BusinessException):
    """未找到数据异常"""
    code = HttpCode.NOT_FOUND


class UnauthorizedException(BusinessException):
    """未授权异常"""
    code = HttpCode.UNAUTHORIZED


class ForbiddenException(BusinessException):
    """无权限异常"""
    code = HttpCode.FORBIDDEN


class ValidateErrorException(BusinessException):
    """数据验证异常"""
    code = HttpCode.VALIDATE_ERROR
