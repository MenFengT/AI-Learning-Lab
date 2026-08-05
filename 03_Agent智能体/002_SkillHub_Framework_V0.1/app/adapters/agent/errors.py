"""Agent Gateway 适配器异常。"""


class AgentAdapterError(Exception):
    """Agent Adapter 异常基类。"""


class AgentRequestConversionError(AgentAdapterError):
    """Gateway 请求无法转换为 Agent Runtime 输入。"""


class AgentInvocationError(AgentAdapterError):
    """注入的 Agent Runtime 调用失败。"""


class AgentResultConversionError(AgentAdapterError):
    """Agent Runtime 结果无法转换为 Gateway 结果。"""
