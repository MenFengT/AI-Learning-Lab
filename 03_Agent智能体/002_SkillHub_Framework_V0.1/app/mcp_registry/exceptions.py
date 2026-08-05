"""MCP Server Registry稳定异常。"""


class MCPRegistryError(Exception):
    """MCP Server Registry异常基类。"""


class DescriptorValidationError(MCPRegistryError, ValueError):
    """Server或Tool描述不符合契约。"""


class DuplicateServerError(MCPRegistryError):
    """相同server_id已存在。"""


class ActiveServerConflictError(MCPRegistryError):
    """同名Server存在多个enabled版本。"""


class ServerNotFoundError(MCPRegistryError):
    """Server不存在。"""


class ServerDisabledError(MCPRegistryError):
    """Server存在但未启用。"""


class ServerUnhealthyError(MCPRegistryError):
    """Server健康状态不允许调用。"""


class ToolNotAllowedError(MCPRegistryError):
    """Tool不在Server固定白名单中。"""


class SecretDetectedError(DescriptorValidationError):
    """Descriptor中发现敏感字段或敏感配置。"""
