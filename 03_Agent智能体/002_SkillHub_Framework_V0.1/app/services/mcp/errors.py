"""MCP传输边界的内部异常类型。"""


class MCPInfrastructureError(Exception):
    """MCP基础设施异常基类。"""


class MCPServerConfigurationError(MCPInfrastructureError):
    """MCP Server配置无效或不可用。"""


class MCPToolNotAllowedError(MCPInfrastructureError):
    """Tool不在Server白名单中。"""


class MCPTransportError(MCPInfrastructureError):
    """Transport通用错误。"""


class MCPTransportTimeoutError(MCPTransportError):
    """单次Transport调用超时。"""


class MCPTransportConnectionError(MCPTransportError):
    """Transport连接失败。"""


class MCPTransportProtocolError(MCPTransportError):
    """Transport收到非法协议响应。"""
