"""固定Office MCP Tool到OfficeCLI隔离端口的协议适配器。"""

from typing import Any, Callable, Mapping

from app.mcp_servers.permissions import (
    DenyAllMCPServerPermissionPolicy,
    MCPServerPermissionPolicyProtocol,
)
from app.services.office.errors import (
    OFFICE_OPERATION_FAILED,
    OFFICE_PERMISSION_DENIED,
    OFFICE_REQUEST_INVALID,
    OFFICE_TOOL_NOT_FOUND,
)

from .models import OfficeCLIAdapterProtocol
from .runtime.errors import OfficeCLIAdapterError
from .tools import OFFICE_ALLOWED_TOOLS, OFFICE_TOOL_DEFINITIONS


class OfficeMCPServerAdapter:
    """只暴露四个固定Tool，不支持万能execute或动态注册。"""

    ALLOWED_TOOLS = OFFICE_ALLOWED_TOOLS
    TOOL_DEFINITIONS = OFFICE_TOOL_DEFINITIONS

    def __init__(
        self,
        office_cli: OfficeCLIAdapterProtocol,
        permission_policy: MCPServerPermissionPolicyProtocol | None = None,
    ) -> None:
        self._office_cli = office_cli
        self._permission_policy = (
            permission_policy or DenyAllMCPServerPermissionPolicy()
        )

    def handle(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            if payload.get("method") != "tools/call":
                return _error(OFFICE_REQUEST_INVALID, "只支持tools/call")
            params = _mapping(payload.get("params"))
            tool_name = params.get("name")
            if tool_name not in self.ALLOWED_TOOLS:
                return _error(OFFICE_TOOL_NOT_FOUND, "Office Tool不存在")
            arguments = _mapping(params.get("arguments", {}))
            _reject_paths(arguments)
            context = _mapping(params.get("_meta"))
            _validate_runtime_context(context)
            definition = next(
                item for item in self.TOOL_DEFINITIONS if item.name == tool_name
            )
            if not self._permission_policy.allows(
                str(context["skill_id"]), definition.permission
            ):
                return _error(OFFICE_PERMISSION_DENIED, "Office Tool权限不足")
            handlers: Mapping[
                str,
                Callable[
                    [Mapping[str, Any], Mapping[str, Any]],
                    Mapping[str, Any],
                ],
            ] = {
                "office.create_document": self._office_cli.create_document,
                "office.update_document": self._office_cli.update_document,
                "office.convert_document": self._office_cli.convert_document,
                "office.export_document": self._office_cli.export_document,
            }
            return {"content": handlers[str(tool_name)](arguments, context)}
        except OfficeCLIAdapterError as exc:
            return _error(exc.error_code, str(exc))
        except (KeyError, TypeError, ValueError) as exc:
            return _error(OFFICE_REQUEST_INVALID, str(exc))
        except Exception as exc:
            return _error(
                OFFICE_OPERATION_FAILED,
                f"OfficeCLI操作失败：{type(exc).__name__}",
            )


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("Office MCP字段必须是对象")
    return value


def _validate_runtime_context(context: Mapping[str, Any]) -> None:
    for field in ("task_id", "trace_id", "span_id", "skill_id"):
        value = context.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"缺少Runtime Context：{field}")


def _reject_paths(arguments: Mapping[str, Any]) -> None:
    forbidden = {"path", "file_path", "absolute_path", "working_directory"}
    for key, value in arguments.items():
        if str(key).casefold() in forbidden:
            raise ValueError("Office Tool禁止直接路径输入")
        if isinstance(value, Mapping):
            _reject_paths(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, Mapping):
                    _reject_paths(item)


def _error(error_code: str, message: str) -> Mapping[str, Any]:
    return {"is_error": True, "error_code": error_code, "message": message}
