"""通用MCP协议客户端：一次调用、无重试、无熔断。"""

from copy import deepcopy
from time import monotonic
from typing import Any, Callable, Mapping

from app.mcp_registry import MCPServerCatalogProtocol
from app.mcp_registry.exceptions import (
    MCPRegistryError,
    ServerDisabledError,
    ServerNotFoundError,
    ServerUnhealthyError,
    ToolNotAllowedError,
)
from app.services.models import MCPRequest, MCPResponse

from .connection_manager import ConnectionManager
from .errors import (
    MCPServerConfigurationError,
    MCPTransportConnectionError,
    MCPTransportProtocolError,
    MCPTransportTimeoutError,
)
from .models import ServerConfig
from .protocols import TransportConfigProviderProtocol


class MCPClient:
    """执行单次MCP Tool协议调用，不包含业务、重试或熔断逻辑。"""

    def __init__(
        self,
        server_catalog: MCPServerCatalogProtocol,
        transport_config_provider: TransportConfigProviderProtocol,
        connection_manager: ConnectionManager,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._server_catalog = server_catalog
        self._transport_config_provider = transport_config_provider
        self._connection_manager = connection_manager
        self._clock = clock

    def call(self, request: MCPRequest) -> MCPResponse:
        started_at = self._clock()

        try:
            descriptor = self._server_catalog.get(request.server_name)
            self._server_catalog.validate_tool(
                request.server_name, request.tool_name
            )
        except ServerNotFoundError:
            return self._error_response(
                request,
                "SHF-MCP-REGISTRY-SERVER_NOT_FOUND",
                "MCP Server不存在",
                started_at,
            )
        except ToolNotAllowedError:
            return self._error_response(
                request,
                "SHF-MCP-REGISTRY-TOOL_NOT_ALLOWED",
                "MCP Tool不在固定白名单",
                started_at,
            )
        except (ServerDisabledError, ServerUnhealthyError):
            return self._error_response(
                request,
                "SHF-MCP-REGISTRY-SERVER_UNHEALTHY",
                "MCP Server不可用",
                started_at,
            )
        except MCPRegistryError:
            return self._error_response(
                request,
                "SHF-MCP-REGISTRY-SERVER_UNHEALTHY",
                "MCP Server目录不可用",
                started_at,
            )

        try:
            config = self._transport_config_provider.resolve(
                descriptor.transport_config_reference
            )
            self._validate_request(request, config)
        except Exception:
            return self._error_response(
                request,
                "SHF-MCP-REGISTRY-TRANSPORT_INVALID",
                "MCP Transport配置无效",
                started_at,
            )

        payload = self._build_payload(request)

        try:
            with self._connection_manager.connection(config) as transport:
                raw_response = transport.send(payload, request.timeout)
            duration_ms = max(0.0, (self._clock() - started_at) * 1000)
            return self._convert_response(request, raw_response, duration_ms)
        except MCPTransportTimeoutError:
            return self._error_response(
                request,
                "SHF-MCP-CLIENT-TIMEOUT",
                "MCP调用超时",
                started_at,
            )
        except MCPTransportConnectionError:
            return self._error_response(
                request,
                "SHF-MCP-CLIENT-CONNECTION",
                "MCP连接失败",
                started_at,
            )
        except MCPTransportProtocolError:
            return self._error_response(
                request,
                "SHF-MCP-PROTOCOL-INVALID_RESPONSE",
                "MCP协议响应无效",
                started_at,
            )

    @staticmethod
    def _validate_request(request: MCPRequest, config: ServerConfig) -> None:
        if request.server_name != config.server_name or not config.enabled:
            raise MCPServerConfigurationError("Transport配置与Server不一致")
        if request.timeout > config.max_request_timeout:
            raise MCPServerConfigurationError(
                "请求timeout超过Server配置上限"
            )
        runtime = request.runtime_context
        required_context = {
            "task_id": runtime.task_id,
            "trace_id": runtime.trace_id,
            "span_id": runtime.span_id,
            "skill_id": runtime.skill_id,
        }
        if any(not value.strip() for value in required_context.values()):
            raise MCPServerConfigurationError("Runtime Context字段不能为空")

    @staticmethod
    def _build_payload(request: MCPRequest) -> Mapping[str, Any]:
        runtime = request.runtime_context
        return {
            "method": "tools/call",
            "params": {
                "name": request.tool_name,
                "arguments": _to_plain(request.arguments),
                "_meta": {
                    "task_id": runtime.task_id,
                    "trace_id": runtime.trace_id,
                    "span_id": runtime.span_id,
                    "skill_id": runtime.skill_id,
                },
            },
        }

    @staticmethod
    def _convert_response(
        request: MCPRequest,
        raw_response: Mapping[str, Any],
        duration_ms: float,
    ) -> MCPResponse:
        if not isinstance(raw_response, Mapping):
            raise MCPTransportProtocolError("MCP响应必须是对象")
        if raw_response.get("is_error", False):
            error_code = raw_response.get("error_code")
            message = raw_response.get("message")
            if not isinstance(error_code, str) or not isinstance(message, str):
                raise MCPTransportProtocolError("MCP错误响应字段无效")
            return MCPResponse(
                success=False,
                content=None,
                error_code=error_code,
                message=message,
                server_name=request.server_name,
                tool_name=request.tool_name,
                trace_id=request.runtime_context.trace_id,
                span_id=request.runtime_context.span_id,
                duration_ms=duration_ms,
                attempts=1,
                metadata={
                    "task_id": request.runtime_context.task_id,
                    "skill_id": request.runtime_context.skill_id,
                },
            )
        if "content" not in raw_response:
            raise MCPTransportProtocolError("MCP成功响应缺少content")
        return MCPResponse(
            success=True,
            content=raw_response["content"],
            error_code=None,
            message="MCP调用成功",
            server_name=request.server_name,
            tool_name=request.tool_name,
            trace_id=request.runtime_context.trace_id,
            span_id=request.runtime_context.span_id,
            duration_ms=duration_ms,
            attempts=1,
            metadata={
                "task_id": request.runtime_context.task_id,
                "skill_id": request.runtime_context.skill_id,
            },
        )
    def _error_response(
        self,
        request: MCPRequest,
        error_code: str,
        message: str,
        started_at: float,
    ) -> MCPResponse:
        return MCPResponse(
            success=False,
            content=None,
            error_code=error_code,
            message=message,
            server_name=request.server_name,
            tool_name=request.tool_name,
            trace_id=request.runtime_context.trace_id,
            span_id=request.runtime_context.span_id,
            duration_ms=max(0.0, (self._clock() - started_at) * 1000),
            attempts=1,
            metadata={
                "task_id": request.runtime_context.task_id,
                "skill_id": request.runtime_context.skill_id,
            },
        )


def _to_plain(value: Any) -> Any:
    """将不可变契约容器转换为Transport可复制的普通协议数据。"""
    if isinstance(value, Mapping):
        return {str(key): _to_plain(child) for key, child in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_to_plain(child) for child in value]
    return deepcopy(value)
