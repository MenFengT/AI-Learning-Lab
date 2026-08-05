from dataclasses import dataclass, field
from typing import Any

from app.runtime.invocation_context import InvocationContext


@dataclass
class TaskContext:
    """在 Agent 与 Skill 之间传递的任务上下文。"""

    user_task: str
    subtasks: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    invocation_context: InvocationContext | None = None
