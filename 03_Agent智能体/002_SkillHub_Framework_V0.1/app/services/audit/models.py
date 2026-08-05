"""Service Layer结构化审计事件模型。"""

from copy import deepcopy
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any, Mapping

from app.services.errors import validate_error_code


_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "content",
        "document_content",
        "file_content",
        "password",
        "secret",
        "token",
    }
)
_REDACTED = "[REDACTED]"


@dataclass(frozen=True)
class AuditEvent:
    task_id: str
    trace_id: str
    span_id: str
    skill_id: str
    server: str
    tool: str
    duration: float
    error_code: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        identifiers = {
            "task_id": self.task_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "skill_id": self.skill_id,
            "server": self.server,
            "tool": self.tool,
        }
        for label, value in identifiers.items():
            if not value.strip():
                raise ValueError(f"{label}不能为空")
        if self.duration < 0:
            raise ValueError("duration不能小于0")
        if self.error_code is not None:
            validate_error_code(self.error_code)
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def sanitized(self) -> "AuditEvent":
        return replace(self, metadata=_redact(self.metadata))


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _REDACTED
            if str(key).casefold() in _SENSITIVE_KEYS
            else _redact(child)
            for key, child in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(_redact(child) for child in value)
    return deepcopy(value)


def _freeze(value: Mapping[str, Any]) -> Mapping[str, Any]:
    copied = deepcopy(dict(value))
    return MappingProxyType(
        {
            key: _freeze_value(child)
            for key, child in copied.items()
        }
    )


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(child) for child in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(child) for child in value)
    return value
