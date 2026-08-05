"""由 Runtime 授权、按确定顺序消费 TaskPlan 的执行适配器。"""

from typing import Any, Mapping

from app.core.context import TaskContext
from app.planner.models import TaskPlan
from app.planner.validators import validate_task_plan
from app.runtime.lifecycle import LifecycleStatus

from .errors import ExecutionStateError, StepExecutionError
from .models import ExecutionResult, StepExecutionResult, StepExecutionStatus
from .protocols import (
    RuntimeExecutionProtocol,
    SkillResolverProtocol,
    SkillRouterProtocol,
)


class TaskPlanExecutor:
    """编排已验证步骤；不持有 Skill，也不接触基础设施能力。"""

    def __init__(
        self,
        runtime: RuntimeExecutionProtocol,
        skill_router: SkillRouterProtocol,
        skill_resolver: SkillResolverProtocol,
    ) -> None:
        self._runtime = runtime
        self._skill_router = skill_router
        self._skill_resolver = skill_resolver

    def execute(self, plan: TaskPlan) -> ExecutionResult:
        validate_task_plan(plan)
        environment = self._runtime.get_environment(plan.task_id)
        status = environment.lifecycle.status
        if status is LifecycleStatus.CREATED:
            self._runtime.transition(plan.task_id, LifecycleStatus.PLANNING)
        elif status is not LifecycleStatus.PLANNING:
            raise ExecutionStateError(
                f"TaskPlan不能在{status.value}状态开始执行"
            )

        step_results: list[StepExecutionResult] = []
        outputs: dict[str, Any] = {}
        self._runtime.transition(plan.task_id, LifecycleStatus.EXECUTING)

        for step in sorted(plan.steps, key=lambda item: item.order):
            try:
                registration = self._skill_router.select_by_id(step.skill_id)
                if registration.skill_id != step.skill_id:
                    raise LookupError("Router返回了不同的skill_id")
                invocation = self._runtime.create_invocation_context(
                    plan.task_id, step.skill_id
                )
                skill = self._skill_resolver.resolve(step.skill_id)
                context = TaskContext(
                    user_task=environment.context.user_request,
                    subtasks=[step.step_id],
                    metadata={
                        "plan_id": plan.plan_id,
                        "step_id": step.step_id,
                        "input_schema": _to_mutable(step.input_schema),
                        "step_inputs": _to_mutable(
                            environment.context.inputs.get(step.step_id, {})
                        ),
                        "dependency_outputs": {
                            dependency: outputs[dependency]
                            for dependency in step.dependency
                        },
                    },
                    invocation_context=invocation,
                )
                output = skill.execute(context)
                outputs[step.step_id] = output
                step_results.append(
                    StepExecutionResult(
                        step_id=step.step_id,
                        skill_id=step.skill_id,
                        span_id=invocation.span_id,
                        status=StepExecutionStatus.COMPLETED,
                        output=output,
                    )
                )
            except Exception as exc:
                self._runtime.fail(plan.task_id, str(exc))
                raise StepExecutionError(
                    step.step_id,
                    step.skill_id,
                    f"计划步骤执行失败：{step.step_id}",
                ) from exc

        result = ExecutionResult(
            plan_id=plan.plan_id,
            task_id=plan.task_id,
            success=True,
            steps=tuple(step_results),
            outputs=outputs,
        )
        self._runtime.complete(plan.task_id, {"plan_result": dict(outputs)})
        return result


def _to_mutable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _to_mutable(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_to_mutable(child) for child in value]
    if isinstance(value, frozenset):
        return {_to_mutable(child) for child in value}
    return value
