"""Service Governance 调用上下文与审计生命周期模型。"""

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
import re
from types import MappingProxyType
from typing import Any, Mapping

from app.runtime.invocation_context import InvocationContext


_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]*$")


class ServiceCallEventType(str, Enum):
    SERVICE_CALL_STARTED = "SERVICE_CALL_STARTED"
    SERVICE_CALL_SUCCEEDED = "SERVICE_CALL_SUCCEEDED"
    SERVICE_CALL_FAILED = "SERVICE_CALL_FAILED"


@dataclass(frozen=True)
class ServiceCallContext:
    """一次 Service 调用的不可变上下文，不包含任何基础设施依赖。"""

    runtime_context: InvocationContext
    service_name: str
    operation_name: str
    service_span_id: str
    parent_span_id: str
    request_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.runtime_context, InvocationContext):
            raise ValueError("runtime_context必须是InvocationContext")
        for label in ("service_name", "operation_name"):
            value = getattr(self, label)
            if not _NAME_PATTERN.fullmatch(value):
                raise ValueError(f"{label}必须是受控小写标识符")
        if not self.service_span_id.strip():
            raise ValueError("service_span_id不能为空")
        if not self.parent_span_id.strip():
            raise ValueError("parent_span_id不能为空")
        if self.parent_span_id != self.runtime_context.span_id:
            raise ValueError("parent_span_id必须指向InvocationContext.span_id")
        if self.service_span_id == self.parent_span_id:
            raise ValueError("service_span_id必须与parent_span_id不同")
        object.__setattr__(
            self,
            "request_metadata",
            _freeze_mapping(self.request_metadata),
        )


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    copied = deepcopy(dict(value))
    return MappingProxyType(
        {key: _freeze_value(child) for key, child in copied.items()}
    )


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(child) for child in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(child) for child in value)
    return value
