"""Service与MCP边界的统一不可变数据契约。"""

from copy import deepcopy
from dataclasses import dataclass, field
import re
from types import MappingProxyType
from typing import Any, Generic, Mapping, TypeVar

from .errors import validate_error_code
from .protocols import RuntimeContextProtocol


T = TypeVar("T")
_ROUTE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]*$")
_SCHEMA_VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_SENSITIVE_KEYS = frozenset(
    {"api_key", "apikey", "password", "secret", "token", "authorization"}
)


@dataclass(frozen=True)
class ServiceResult(Generic[T]):
    success: bool
    data: T | None
    error_code: str | None
    message: str
    trace_id: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        if not self.trace_id.strip():
            raise ValueError("trace_id不能为空")
        if not self.message.strip():
            raise ValueError("message不能为空")
        if not _SCHEMA_VERSION_PATTERN.fullmatch(self.schema_version):
            raise ValueError("schema_version格式无效")
        if self.success and self.error_code is not None:
            raise ValueError("成功结果的error_code必须为None")
        if not self.success:
            if self.error_code is None:
                raise ValueError("失败结果必须包含error_code")
            validate_error_code(self.error_code)
        _reject_sensitive_keys(self.data, "data")
        _reject_sensitive_keys(self.metadata, "metadata")
        object.__setattr__(self, "data", deepcopy(self.data))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True)
class MCPRequest:
    """只能由Service根据受控配置构建，禁止直接采用用户指定路由。"""

    server_name: str
    tool_name: str
    arguments: Mapping[str, Any]
    runtime_context: RuntimeContextProtocol
    timeout: float

    def __post_init__(self) -> None:
        _validate_route_name(self.server_name, "server_name")
        _validate_route_name(self.tool_name, "tool_name")
        if self.timeout <= 0:
            raise ValueError("timeout必须大于0")
        if not self.runtime_context.trace_id.strip():
            raise ValueError("runtime_context.trace_id不能为空")
        if not self.runtime_context.span_id.strip():
            raise ValueError("runtime_context.span_id不能为空")
        object.__setattr__(self, "arguments", _freeze_mapping(self.arguments))


@dataclass(frozen=True)
class MCPResponse:
    success: bool
    content: Any | None
    error_code: str | None
    message: str
    server_name: str
    tool_name: str
    trace_id: str
    span_id: str
    duration_ms: float
    attempts: int
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_route_name(self.server_name, "server_name")
        _validate_route_name(self.tool_name, "tool_name")
        if not self.trace_id.strip() or not self.span_id.strip():
            raise ValueError("trace_id和span_id不能为空")
        if not self.message.strip():
            raise ValueError("message不能为空")
        if self.duration_ms < 0:
            raise ValueError("duration_ms不能小于0")
        if self.attempts < 1:
            raise ValueError("attempts必须至少为1")
        if self.success and self.error_code is not None:
            raise ValueError("成功响应的error_code必须为None")
        if not self.success:
            if self.error_code is None:
                raise ValueError("失败响应必须包含error_code")
            validate_error_code(self.error_code)
        _reject_sensitive_keys(self.metadata, "metadata")
        object.__setattr__(self, "content", deepcopy(self.content))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


def _validate_route_name(value: str, label: str) -> None:
    if not _ROUTE_NAME_PATTERN.fullmatch(value):
        raise ValueError(f"{label}必须是受控小写标识符：{value}")


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    copied = deepcopy(dict(value))
    return MappingProxyType(
        {key: _freeze_value(child) for key, child in copied.items()}
    )


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze_value(item) for item in value)
    return value


def _reject_sensitive_keys(value: Any, location: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = str(key).casefold()
            if normalized_key in _SENSITIVE_KEYS:
                raise ValueError(f"{location}禁止包含敏感字段：{key}")
            _reject_sensitive_keys(child, location)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            _reject_sensitive_keys(child, location)
