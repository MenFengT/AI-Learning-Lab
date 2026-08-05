import unittest
from datetime import datetime, timezone

from app.execution import TaskPlanExecutor
from app.planner.errors import PlanValidationError
from app.planner.models import PlanStep, TaskPlan
from app.runtime.lifecycle import LifecycleStatus
from app.runtime.runtime_manager import RuntimeManager


class NeverCalled:
    def __getattr__(self, name: str) -> object:
        raise AssertionError(f"验证失败前不应访问依赖：{name}")


class ExecutionValidationTests(unittest.TestCase):
    def test_cyclic_dependency_is_rejected_before_runtime_changes(self) -> None:
        runtime = RuntimeManager()
        environment = runtime.create_environment("循环依赖测试")
        plan = TaskPlan(
            plan_id="plan-cycle",
            task_id=environment.context.task_id,
            created_at=datetime.now(timezone.utc),
            steps=(
                PlanStep(
                    "step-1",
                    1,
                    "local/first@0.3.0",
                    {"type": "object"},
                    ("step-2",),
                    {"type": "object"},
                ),
                PlanStep(
                    "step-2",
                    2,
                    "local/second@0.3.0",
                    {"type": "object"},
                    ("step-1",),
                    {"type": "object"},
                ),
            ),
        )
        executor = TaskPlanExecutor(runtime, NeverCalled(), NeverCalled())

        with self.assertRaises(PlanValidationError):
            executor.execute(plan)

        self.assertEqual(
            runtime.get_environment(environment.context.task_id).lifecycle.status,
            LifecycleStatus.CREATED,
        )


if __name__ == "__main__":
    unittest.main()
