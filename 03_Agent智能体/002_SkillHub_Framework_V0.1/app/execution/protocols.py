"""TaskPlan 执行所需的最小依赖协议。"""

from typing import Any, Protocol

from app.core.context import TaskContext
from app.planner.models import TaskPlan
from app.registry.models import SkillRegistration
from app.runtime.invocation_context import InvocationContext
from app.runtime.lifecycle import LifecycleStatus
from app.runtime.runtime_manager import RuntimeEnvironment

from .models import ExecutionResult


class SkillExecutableProtocol(Protocol):
    def execute(self, context: TaskContext) -> str: ...


class SkillResolverProtocol(Protocol):
    def resolve(self, skill_id: str) -> SkillExecutableProtocol: ...


class SkillRouterProtocol(Protocol):
    def select_by_id(self, skill_id: str) -> SkillRegistration: ...


class RuntimeExecutionProtocol(Protocol):
    def get_environment(self, task_id: str) -> RuntimeEnvironment: ...

    def transition(self, task_id: str, next_status: LifecycleStatus) -> None: ...

    def create_invocation_context(
        self, task_id: str, skill_id: str
    ) -> InvocationContext: ...

    def complete(
        self, task_id: str, outputs: dict[str, Any] | None = None
    ) -> None: ...

    def fail(self, task_id: str, error: str) -> None: ...


class TaskPlanExecutorProtocol(Protocol):
    def execute(self, plan: TaskPlan) -> ExecutionResult: ...
