"""TaskPlan 执行结果模型。"""

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


class StepExecutionStatus(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class StepExecutionResult:
    """单个计划步骤的可审计执行结果。"""

    step_id: str
    skill_id: str
    span_id: str
    status: StepExecutionStatus
    output: Any = None
    error: str | None = None


@dataclass(frozen=True)
class ExecutionResult:
    """成功消费一个 TaskPlan 后的聚合结果。"""

    plan_id: str
    task_id: str
    success: bool
    steps: tuple[StepExecutionResult, ...]
    outputs: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "steps", tuple(self.steps))
        object.__setattr__(
            self,
            "outputs",
            MappingProxyType(deepcopy(dict(self.outputs))),
        )
