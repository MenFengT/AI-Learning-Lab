import unittest
from datetime import datetime, timezone

from app.planner import (
    PlanStep,
    PlanStepStatus,
    PlanValidationError,
    TaskPlan,
    validate_task_plan,
)


SCHEMA = {"type": "object", "properties": {}}


def plan(*steps: PlanStep) -> TaskPlan:
    return TaskPlan(
        plan_id="plan-001",
        task_id="task-001",
        created_at=datetime(2026, 8, 4, tzinfo=timezone.utc),
        steps=steps,
    )


def step(
    step_id: str,
    order: int,
    *,
    dependency: tuple[str, ...] = (),
    status: PlanStepStatus = PlanStepStatus.PENDING,
    input_schema: dict[str, object] | None = None,
) -> PlanStep:
    return PlanStep(
        step_id=step_id,
        order=order,
        skill_id="local/example@0.3.0",
        input_schema=input_schema or SCHEMA,
        dependency=dependency,
        expected_output=SCHEMA,
        status=status,
    )


class PlanValidationTests(unittest.TestCase):
    def test_valid_ordered_dependencies(self) -> None:
        task_plan = plan(
            step("step-1", 1),
            step("step-2", 2, dependency=("step-1",)),
        )

        validate_task_plan(task_plan)

    def test_rejects_duplicate_steps_and_non_contiguous_order(self) -> None:
        with self.assertRaisesRegex(PlanValidationError, "step_id"):
            validate_task_plan(plan(step("same", 1), step("same", 2)))
        with self.assertRaisesRegex(PlanValidationError, "连续"):
            validate_task_plan(plan(step("step-1", 1), step("step-2", 3)))

    def test_rejects_missing_forward_and_self_dependencies(self) -> None:
        cases = (
            (plan(step("step-1", 1, dependency=("missing",))), "当前计划"),
            (
                plan(
                    step("step-1", 1),
                    step("step-2", 2, dependency=("step-2",)),
                ),
                "自身",
            ),
            (
                plan(
                    step("step-1", 1, dependency=("step-2",)),
                    step("step-2", 2),
                ),
                "更早",
            ),
        )
        for task_plan, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(PlanValidationError, message):
                    validate_task_plan(task_plan)

    def test_rejects_runtime_status_and_invalid_schema(self) -> None:
        with self.assertRaisesRegex(PlanValidationError, "PENDING"):
            validate_task_plan(
                plan(step("step-1", 1, status=PlanStepStatus.RUNNING))
            )
        with self.assertRaisesRegex(PlanValidationError, "type"):
            validate_task_plan(
                plan(
                    step(
                        "step-1",
                        1,
                        input_schema={"type": "array", "properties": {}},
                    )
                )
            )

    def test_max_steps_is_finite(self) -> None:
        with self.assertRaisesRegex(PlanValidationError, "最大"):
            validate_task_plan(
                plan(step("step-1", 1), step("step-2", 2)),
                max_steps=1,
            )


if __name__ == "__main__":
    unittest.main()
