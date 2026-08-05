"""TaskPlan结构、Schema和依赖图校验。"""

from collections.abc import Mapping
from typing import Any

from .errors import PlanValidationError
from .models import PlanStepStatus, TaskPlan


_SCHEMA_TYPES = frozenset(
    {"string", "integer", "number", "boolean", "object", "array", "null"}
)


def validate_task_plan(plan: TaskPlan, *, max_steps: int = 100) -> None:
    """校验Planner初始计划；不执行也不推进状态。"""
    if not isinstance(plan, TaskPlan):
        raise PlanValidationError("plan必须是TaskPlan")
    if max_steps < 1:
        raise PlanValidationError("max_steps必须大于0")
    if not plan.steps:
        raise PlanValidationError("TaskPlan至少包含一个Step")
    if len(plan.steps) > max_steps:
        raise PlanValidationError("TaskPlan超过最大Step数量")

    step_ids = tuple(step.step_id for step in plan.steps)
    orders = tuple(step.order for step in plan.steps)
    if len(set(step_ids)) != len(step_ids):
        raise PlanValidationError("step_id不能重复")
    if len(set(orders)) != len(orders):
        raise PlanValidationError("order不能重复")
    if tuple(sorted(orders)) != tuple(range(1, len(plan.steps) + 1)):
        raise PlanValidationError("order必须从1开始连续递增")

    order_by_id = {step.step_id: step.order for step in plan.steps}
    for step in plan.steps:
        if step.status is not PlanStepStatus.PENDING:
            raise PlanValidationError("Planner只能生成PENDING状态的Step")
        _validate_json_schema(step.input_schema, "input_schema")
        _validate_json_schema(step.expected_output, "expected_output")
        for dependency in step.dependency:
            if dependency not in order_by_id:
                raise PlanValidationError("dependency必须引用当前计划中的Step")
            if dependency == step.step_id:
                raise PlanValidationError("Step不能依赖自身")
            if order_by_id[dependency] >= step.order:
                raise PlanValidationError("Step只能依赖执行顺序更早的Step")
    _validate_acyclic(plan)


def _validate_json_schema(schema: Mapping[str, Any], label: str) -> None:
    if schema.get("type") != "object":
        raise PlanValidationError(f"{label}.type必须为object")
    properties = schema.get("properties", {})
    if not isinstance(properties, Mapping):
        raise PlanValidationError(f"{label}.properties必须是对象")
    required = schema.get("required", ())
    if not isinstance(required, (list, tuple)):
        raise PlanValidationError(f"{label}.required必须是数组")
    if any(not isinstance(item, str) for item in required):
        raise PlanValidationError(f"{label}.required只能包含字段名")
    if len(set(required)) != len(required):
        raise PlanValidationError(f"{label}.required不能重复")
    for field_name, field_schema in properties.items():
        if not isinstance(field_name, str) or not field_name:
            raise PlanValidationError(f"{label}字段名不能为空")
        if not isinstance(field_schema, Mapping):
            raise PlanValidationError(f"{label}.{field_name}必须是对象")
        if field_schema.get("type") not in _SCHEMA_TYPES:
            raise PlanValidationError(f"{label}.{field_name}.type无效")
    if any(field not in properties for field in required):
        raise PlanValidationError(f"{label}.required引用了未声明字段")


def _validate_acyclic(plan: TaskPlan) -> None:
    dependencies = {
        step.step_id: tuple(step.dependency) for step in plan.steps
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(step_id: str) -> None:
        if step_id in visiting:
            raise PlanValidationError("TaskPlan dependency存在循环")
        if step_id in visited:
            return
        visiting.add(step_id)
        for dependency in dependencies[step_id]:
            visit(dependency)
        visiting.remove(step_id)
        visited.add(step_id)

    for step_id in dependencies:
        visit(step_id)
