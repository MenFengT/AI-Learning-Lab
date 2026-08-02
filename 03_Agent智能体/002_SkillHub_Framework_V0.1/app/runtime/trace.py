"""提供 Runtime 链路标识生成与父子链路关联能力。"""

from dataclasses import dataclass
from uuid import uuid4


def generate_trace_id() -> str:
    """生成不依赖外部服务的全局链路标识。"""
    return uuid4().hex


def generate_span_id() -> str:
    """生成链路内执行节点的唯一标识。"""
    return uuid4().hex


@dataclass(frozen=True)
class Trace:
    """描述一次根链路或子链路。"""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None

    @classmethod
    def create(cls) -> "Trace":
        return cls(trace_id=generate_trace_id(), span_id=generate_span_id())

    def create_child(self) -> "Trace":
        """创建与当前链路关联的子链路。"""
        return Trace(
            trace_id=self.trace_id,
            span_id=generate_span_id(),
            parent_span_id=self.span_id,
        )
