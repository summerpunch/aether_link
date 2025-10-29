from enum import Enum


class ErrorCode(Enum):
    HTTP_200_OK = (2000, "OK")

    INTERNAL_SERVER_ERROR = (5000, "服务器内部错误")

    BUSINESS_ERROR = (4000, "BUSINESS_ERROR")

    BUSINESS_REGISTER_ERROR = (4100, "注册失败，请稍后重试")

    BUSINESS_REGISTER_EMAIL_ERROR = (4101, "该邮箱已被注册")

    BUSINESS_LOGIN_INTERNAL_ERROR = (4102, "邮箱或密码不正确")

    BUSINESS_TOKEN_URL_INTERNAL_ERROR = (4103, "无效、已过期或已使用的链接")

    BUSINESS_EMAIL_VERIFIED_ERROR = (4104, "邮箱未激活")

    BUSINESS_EMAIL_MAILBOX_NOT_FOUND_ERROR = (4105, "找不到或拒绝访问的邮箱")

    BUSINESS_INVITE_CODE_NOT_FOUND_ERROR = (4106, "邀请码不能为空")

    BUSINESS_INVITE_CODE_EXPIRES_ERROR = (4107, "邀请码已过期")

    BUSINESS_INVITE_CODE_DATA_NOT_FOUND_ERROR = (4108, "邀请码不存在")

    BUSINESS_INVITE_CODE_USAGE_MAX_ERROR = (4109, "邀请码已超过最大使用量")

    BUSINESS_INVITE_CODE_INACTIVE_ERROR = (4110, "邀请码已失效")

    BUSINESS_DATA_NOT_FOUND_ERROR = (4200, "用户数据不存在")

    BUSINESS_CHAT_SESSION_FORBIDDEN_ERROR = (4300, "禁止访问")

    BUSINESS_CHAT_SESSION_TERMINATION_ERROR = (4301, "会话已结束")

    BUSINESS_CHAT_SESSION_NOT_FOUND_ERROR = (4302, "会话不存在")

    BUSINESS_CHAT_SESSION_LOCK_ERROR = (4303, "会话正在进行中")

    BUSINESS_CHAT_SESSION_REMOVE_ERROR = (4304, "删除失败或会话不存在")

    BUSINESS_CHAT_SESSION_PROCESS_ERROR = (4305, "当前{} ,无法继续进行")

    SESSION_RUNNING_COUNT_ERROR = (4306, "当前运行中的规划任务数量已达到上限，请稍后再试")

    SESSION_TODAY_COUNT_ERROR = (4307, "当日提交的规划任务数量已达到上限，请明日再试")

    BUSINESS_CHAT_SESSION_RUNNING_ERROR = (4308, "当前会话无活跃工作流")

    BUSINESS_CHAT_SESSION_SUCCESS_ERROR = (4309, "会话未完成,请稍后再试")

    BUSINESS_CHAT_SESSION_REPORT_ERROR = (4310, "报告格式不符合预期")

    BUSINESS_KNOWLEDGE_DATA_NOT_FOUND_ERROR = (4311, "知识库不存在")

    BUSINESS_KNOWLEDGE_FILE_DATA_NOT_FOUND_ERROR = (4312, "知识库文件不存在")

    BUSINESS_KNOWLEDGE_REMOVE_ERROR = (4313, "知识库删除失败")

    BUSINESS_KNOWLEDGE_FILE_REMOVE_ERROR = (4314, "知识库文件删除失败")

    BUSINESS_KNOWLEDGE_NAME_DUPLICATE_ERROR = (4315, "知识库名称已存在")

    BUSINESS_KNOWLEDGE_NUMBER_LIMIT_ERROR = (4316, "个人知识库数量已达上限")

    BUSINESS_KNOWLEDGE_DOCUMENT_FILE_NOT_FOUND_ERROR = (4317, "知识库文件列表不能为空")

    BUSINESS_KNOWLEDGE_DOCUMENT_FILE_NUMBER_LIMIT_ERROR = (4318, "单次文件上传数量已达上限")

    BUSINESS_KNOWLEDGE_DOCUMENT_FILE_SIZE_ERROR = (4319, "文件 {} ,大小已达上限")

    BUSINESS_KNOWLEDGE_DOCUMENT_FILE_TOTAL_SIZE_ERROR = (4320, "文件列表总大小已达上限")

    BUSINESS_KNOWLEDGE_DOCUMENT_FILE_TYPE_ERROR = (4320, "文件格式不符合预期")

    BUSINESS_KNOWLEDGE_DOCUMENT_USER_FILE_TOTAL_LIMIT_ERROR = (4321, "个人文件总数已达上限")

    BUSINESS_KNOWLEDGE_DOCUMENT_UPLOADING_ERROR = (4322, "知识库有正在上传的文件, 不允许删除")

    UNAUTHORIZED_ERROR = (4010, "UNAUTHORIZED")

    BUSINESS_SHARE_REPORT_ERROR = (4303, "分享不存在")

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message

    def supplement_message(self, *args):
        return self.message.format(*args)


if __name__ == "__main__":
    err = ErrorCode.BUSINESS_CHAT_SESSION_PROCESS_ERROR
    print(err.code)  # 输出: 4100
    print(err.supplement_message("请稍后重试"))
    print(err.message)
