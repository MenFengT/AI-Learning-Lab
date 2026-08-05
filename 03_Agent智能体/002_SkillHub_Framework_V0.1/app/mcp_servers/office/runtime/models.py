"""OfficeCLI 安全调用模型。"""

from dataclasses import dataclass, field
from types import MappingProxyType, ModuleType
from typing import Any, Mapping

from app.services.filesystem.models import FileReference

from .errors import OfficeCLIRequestError, OfficeCLIResponseError


@dataclass(frozen=True)
class OfficeCLIRequest:
    operation: str
    arguments: Mapping[str, Any]
    task_id: str
    trace_id: str
    span_id: str
    skill_id: str

    def __post_init__(self) -> None:
        if self.operation not in {
            "create_document",
            "update_document",
            "convert_document",
            "export_document",
        }:
            raise OfficeCLIRequestError("OfficeCLI操作不在固定白名单")
        for value in (self.task_id, self.trace_id, self.span_id, self.skill_id):
            if not isinstance(value, str) or not value.strip():
                raise OfficeCLIRequestError("Runtime Context不完整")
        _validate_arguments(self.arguments)
        object.__setattr__(self, "arguments", _freeze_mapping(self.arguments))


@dataclass(frozen=True)
class OfficeCLIResult:
    file_reference: FileReference
    format: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.file_reference, FileReference):
            raise OfficeCLIResponseError("OfficeCLI输出必须经过FileReference流程")
        if not isinstance(self.format, str) or not self.format.strip():
            raise OfficeCLIResponseError("OfficeCLI输出格式无效")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


_FORBIDDEN_KEYS = frozenset(
    {
        "absolute_path",
        "args",
        "arguments_string",
        "cmd",
        "command",
        "cwd",
        "executable",
        "file_path",
        "path",
        "shell",
        "working_directory",
    }
)


def _validate_arguments(value: Any) -> None:
    if callable(value) or isinstance(value, ModuleType):
        raise OfficeCLIRequestError("OfficeCLI参数禁止可执行对象")
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if normalized in _FORBIDDEN_KEYS:
                raise OfficeCLIRequestError(f"OfficeCLI禁止参数：{key}")
            _validate_arguments(child)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for child in value:
            _validate_arguments(child)
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise OfficeCLIRequestError("OfficeCLI参数类型不安全")


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OfficeCLIRequestError("OfficeCLI参数必须是Mapping")
    return MappingProxyType({str(key): _freeze_value(child) for key, child in value.items()})


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(child) for child in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(child) for child in value)
    return value
