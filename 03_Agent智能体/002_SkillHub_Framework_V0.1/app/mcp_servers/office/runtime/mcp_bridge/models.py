"""OfficeCLI MCP Bridge 的固定协议模型。"""

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType, ModuleType
from typing import Any, Mapping

from .errors import BridgeRequestError, BridgeResponseError


class OfficeCLIBridgeTool(str, Enum):
    """Bridge V0.3 固定Tool；不允许运行时发现或扩展。"""

    CREATE_DOCUMENT = "officecli.create_document"
    UPDATE_DOCUMENT = "officecli.update_document"
    CONVERT_DOCUMENT = "officecli.convert_document"
    EXPORT_DOCUMENT = "officecli.export_document"


@dataclass(frozen=True)
class OfficeCLIMCPCall:
    tool: OfficeCLIBridgeTool
    arguments: Mapping[str, Any]
    task_id: str
    trace_id: str
    span_id: str
    skill_id: str
    timeout: float = 30.0

    def __post_init__(self) -> None:
        if not isinstance(self.tool, OfficeCLIBridgeTool):
            raise BridgeRequestError("Bridge Tool不在固定白名单")
        for value in (self.task_id, self.trace_id, self.span_id, self.skill_id):
            if not isinstance(value, str) or not value.strip():
                raise BridgeRequestError("Runtime Context不完整")
        if self.timeout <= 0:
            raise BridgeRequestError("timeout必须大于0")
        _validate_safe(self.arguments)
        object.__setattr__(self, "arguments", _freeze_mapping(self.arguments))


@dataclass(frozen=True)
class OfficeCLIMCPResult:
    success: bool
    content: Mapping[str, Any] | None
    error_code: str | None = None
    message: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.success and self.error_code is not None:
            raise BridgeResponseError("成功响应不能包含error_code")
        if not self.success and not self.error_code:
            raise BridgeResponseError("失败响应必须包含error_code")
        if self.content is not None:
            _validate_safe(self.content)
            object.__setattr__(self, "content", _freeze_mapping(self.content))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


_FORBIDDEN_KEYS = frozenset(
    {
        "absolute_path", "args", "cmd", "command", "cwd", "executable",
        "file_path", "path", "shell", "working_directory",
    }
)


def _validate_safe(value: Any) -> None:
    if callable(value) or isinstance(value, ModuleType):
        raise BridgeRequestError("Bridge禁止可执行对象")
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold().replace("-", "_") in _FORBIDDEN_KEYS:
                raise BridgeRequestError(f"Bridge禁止参数：{key}")
            _validate_safe(child)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for child in value:
            _validate_safe(child)
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise BridgeRequestError("Bridge参数类型不安全")


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BridgeRequestError("Bridge数据必须是Mapping")
    return MappingProxyType({str(key): _freeze_value(child) for key, child in value.items()})


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(child) for child in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(child) for child in value)
    return value
