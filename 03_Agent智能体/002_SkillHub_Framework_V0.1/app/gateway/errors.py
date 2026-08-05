"""Interaction Gateway错误。"""


class GatewayError(RuntimeError):
    """Gateway基础错误。"""


class GatewayValidationError(GatewayError, ValueError):
    """用户消息或Agent结果不符合契约。"""


class GatewayInvocationError(GatewayError):
    """Agent调用适配失败。"""
