"""MCP Server Registry不可变、安全数据契约。"""

from dataclasses import dataclass, field
from enum import Enum
import re
from types import MappingProxyType, ModuleType
from typing import Any, Mapping

from .exceptions import DescriptorValidationError, SecretDetectedError


_SERVER_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
_TOOL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*\.[a-z][a-z0-9_.-]*$")
_VERSION_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
_SCHEMA_VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]*$")
_PERMISSION_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
_SENSITIVE_KEYS = frozenset(
    {"token", "password", "api_key", "apikey", "secret", "authorization"}
)
_CODE_MARKERS = (
    "__import__",
    "eval(",
    "exec(",
    "os.system",
    "subprocess",
    "lambda ",
    "import ",
)


class TransportType(str, Enum):
    STDIO = "STDIO"
    HTTP = "HTTP"
    SSE = "SSE"
    IN_MEMORY = "IN_MEMORY"


class ServerCapability(str, Enum):
    TOOLS = "TOOLS"
    RESOURCES = "RESOURCES"
    PROMPTS = "PROMPTS"
    STREAMING = "STREAMING"


class ServerHealthStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


class ToolIdempotency(str, Enum):
    IDEMPOTENT = "IDEMPOTENT"
    IDEMPOTENT_WITH_KEY = "IDEMPOTENT_WITH_KEY"
    NON_IDEMPOTENT = "NON_IDEMPOTENT"


@dataclass(frozen=True)
class ServerCapabilities:
    tools: bool
    resources: bool = False
    prompts: bool = False
    streaming: bool = False

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, bool)
            for value in (
                self.tools,
                self.resources,
                self.prompts,
                self.streaming,
            )
        ):
            raise DescriptorValidationError(
                "Capability声明必须是bool"
            )

    def supports(self, capability: ServerCapability) -> bool:
        mapping = {
            ServerCapability.TOOLS: self.tools,
            ServerCapability.RESOURCES: self.resources,
            ServerCapability.PROMPTS: self.prompts,
            ServerCapability.STREAMING: self.streaming,
        }
        return mapping[capability]


@dataclass(frozen=True)
class ToolDescriptor:
    tool_name: str
    description: str
    input_schema: Mapping[str, Any]
    output_schema: Mapping[str, Any]
    permission_required: str
    idempotency: ToolIdempotency

    def __post_init__(self) -> None:
        if not _TOOL_NAME_PATTERN.fullmatch(self.tool_name):
            raise DescriptorValidationError(
                f"tool_name格式无效：{self.tool_name}"
            )
        if not isinstance(self.description, str) or not self.description.strip():
            raise DescriptorValidationError("Tool description不能为空")
        if not isinstance(
            self.permission_required, str
        ) or not _PERMISSION_PATTERN.fullmatch(self.permission_required):
            raise DescriptorValidationError(
                "permission_required必须是受控大写权限标识"
            )
        if not isinstance(self.idempotency, ToolIdempotency):
            raise DescriptorValidationError(
                "idempotency必须是ToolIdempotency"
            )
        object.__setattr__(
            self,
            "input_schema",
            _freeze_safe_mapping(self.input_schema, "input_schema"),
        )
        object.__setattr__(
            self,
            "output_schema",
            _freeze_safe_mapping(self.output_schema, "output_schema"),
        )


@dataclass(frozen=True)
class MCPServerDescriptor:
    server_id: str
    server_name: str
    version: str
    description: str
    transport_type: TransportType
    transport_config_reference: str
    capabilities: ServerCapabilities
    allowed_tools: tuple[ToolDescriptor, ...]
    health_status: ServerHealthStatus = ServerHealthStatus.UNKNOWN
    enabled: bool = True
    schema_version: str = "0.1"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_server_name(self.server_name)
        validate_version(self.version)
        expected_id = build_server_id(self.server_name, self.version)
        if self.server_id != expected_id:
            raise DescriptorValidationError(
                f"server_id必须为：{expected_id}"
            )
        if not isinstance(self.description, str) or not self.description.strip():
            raise DescriptorValidationError("Server description不能为空")
        if not isinstance(self.transport_type, TransportType):
            raise DescriptorValidationError(
                "transport_type必须是TransportType"
            )
        validate_transport_reference(self.transport_config_reference)
        if not isinstance(self.capabilities, ServerCapabilities):
            raise DescriptorValidationError(
                "capabilities必须是ServerCapabilities"
            )
        tools = tuple(self.allowed_tools)
        if any(not isinstance(tool, ToolDescriptor) for tool in tools):
            raise DescriptorValidationError(
                "allowed_tools只能包含ToolDescriptor"
            )
        names = tuple(tool.tool_name for tool in tools)
        if len(set(names)) != len(names):
            raise DescriptorValidationError("Tool名称不能重复")
        if self.capabilities.tools and not tools:
            raise DescriptorValidationError(
                "声明TOOLS能力时必须提供allowed_tools"
            )
        if not self.capabilities.tools and tools:
            raise DescriptorValidationError(
                "未声明TOOLS能力时allowed_tools必须为空"
            )
        if not isinstance(self.health_status, ServerHealthStatus):
            raise DescriptorValidationError(
                "health_status必须是ServerHealthStatus"
            )
        if not isinstance(self.enabled, bool):
            raise DescriptorValidationError("enabled必须是bool")
        if not isinstance(
            self.schema_version, str
        ) or not _SCHEMA_VERSION_PATTERN.fullmatch(self.schema_version):
            raise DescriptorValidationError("schema_version格式无效")
        object.__setattr__(self, "allowed_tools", tools)
        object.__setattr__(
            self,
            "metadata",
            _freeze_safe_mapping(self.metadata, "metadata"),
        )

    def tool(self, tool_name: str) -> ToolDescriptor | None:
        return next(
            (tool for tool in self.allowed_tools if tool.tool_name == tool_name),
            None,
        )


def build_server_id(server_name: str, version: str) -> str:
    validate_server_name(server_name)
    validate_version(version)
    return f"{server_name}@{version}"


def validate_server_name(server_name: str) -> None:
    if not _SERVER_NAME_PATTERN.fullmatch(server_name):
        raise DescriptorValidationError(
            f"server_name格式无效：{server_name}"
        )


def validate_version(version: str) -> None:
    if not _VERSION_PATTERN.fullmatch(version):
        raise DescriptorValidationError(f"version格式无效：{version}")


def validate_transport_reference(reference: str) -> None:
    normalized = reference.casefold()
    if not _REFERENCE_PATTERN.fullmatch(reference):
        raise DescriptorValidationError(
            "transport_config_reference必须是受控配置引用"
        )
    if _contains_sensitive_name(normalized):
        raise SecretDetectedError(
            "transport_config_reference包含敏感字段"
        )


def _freeze_safe_mapping(
    value: Mapping[str, Any], location: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DescriptorValidationError(f"{location}必须是Mapping")
    frozen: dict[str, Any] = {}
    for key, child in value.items():
        if not isinstance(key, str):
            raise DescriptorValidationError(f"{location}的键必须是str")
        normalized_key = key.casefold().replace("-", "_")
        if _contains_sensitive_name(normalized_key):
            raise SecretDetectedError(f"{location}包含敏感字段：{key}")
        frozen[key] = _freeze_safe_value(child, f"{location}.{key}")
    return MappingProxyType(frozen)


def _freeze_safe_value(value: Any, location: str) -> Any:
    if callable(value) or isinstance(value, ModuleType):
        raise DescriptorValidationError(f"{location}禁止保存可执行对象")
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        normalized = value.casefold()
        if any(marker in normalized for marker in _CODE_MARKERS):
            raise DescriptorValidationError(f"{location}禁止代码字符串")
        return value
    if isinstance(value, Mapping):
        return _freeze_safe_mapping(value, location)
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_safe_value(child, f"{location}[]") for child in value
        )
    if isinstance(value, (set, frozenset)):
        return frozenset(
            _freeze_safe_value(child, f"{location}[]") for child in value
        )
    raise DescriptorValidationError(
        f"{location}只允许安全基础数据，实际为{type(value).__name__}"
    )


def _contains_sensitive_name(value: str) -> bool:
    normalized = value.casefold().replace("-", "_").replace(".", "_")
    parts = tuple(part for part in normalized.split("_") if part)
    return any(
        sensitive == normalized
        or sensitive in parts
        or normalized.endswith(f"_{sensitive}")
        for sensitive in _SENSITIVE_KEYS
    )
