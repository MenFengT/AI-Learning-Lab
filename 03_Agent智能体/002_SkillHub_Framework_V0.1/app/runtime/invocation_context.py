"""定义一次 Skill 调用使用的统一、只读运行上下文。"""

from copy import deepcopy
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True)
class InvocationContext:
    """贯穿 Agent、Skill、Service、MCP 与 Audit 的调用标识。"""

    task_id: str
    trace_id: str
    span_id: str
    skill_id: str
    user_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("task_id", "trace_id", "span_id", "skill_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name}不能为空")
        if self.user_id is not None and not self.user_id.strip():
            raise ValueError("user_id不能为空字符串")
        object.__setattr__(
            self,
            "metadata",
            _freeze_mapping(self.metadata),
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
