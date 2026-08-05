"""Content Service输入契约。"""

from copy import deepcopy
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from app.runtime.invocation_context import InvocationContext


@dataclass(frozen=True)
class ContentServiceRequest:
    runtime_context: InvocationContext
    document_type: str
    title: str
    requirements: str
    requested_sections: tuple[str, ...] = ()
    knowledge_query: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    timeout: float = 10.0

    def __post_init__(self) -> None:
        for label in ("document_type", "title", "requirements"):
            value = getattr(self, label)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label}不能为空")
        requested = tuple(item.strip() for item in self.requested_sections)
        if any(not item for item in requested):
            raise ValueError("requested_sections不能包含空值")
        if self.knowledge_query is not None and not self.knowledge_query.strip():
            raise ValueError("knowledge_query不能为空字符串")
        if self.timeout <= 0:
            raise ValueError("timeout必须大于0")
        object.__setattr__(self, "requested_sections", requested)
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(deepcopy(dict(self.metadata))),
        )
