"""统一任务执行上下文，不替代 V0.1 的 TaskContext。"""

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionContext:
    """记录一次 Runtime 执行所需的输入、输出与链路信息。"""

    task_id: str
    trace_id: str
    user_request: str
    user_id: str | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        """隔离调用方传入的嵌套可变数据。"""
        self.inputs = deepcopy(self.inputs)
        self.outputs = deepcopy(self.outputs)
        self.metadata = deepcopy(self.metadata)
