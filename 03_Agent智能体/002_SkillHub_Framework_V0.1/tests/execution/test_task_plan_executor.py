import unittest
from datetime import datetime, timezone

from app.core.context import TaskContext
from app.core.skill_resolver import InMemorySkillResolver
from app.core.skill_router import SkillRouter
from app.execution import StepExecutionError, TaskPlanExecutor
from app.planner.models import PlanStep, TaskPlan
from app.registry import (
    HealthStatus,
    SkillLifecycleStatus,
    SkillMetadata,
    SkillRegistration,
    SkillRegistry,
)
from app.runtime.lifecycle import LifecycleStatus
from app.runtime.runtime_manager import RuntimeManager


def make_registration(name: str) -> SkillRegistration:
    version = "0.3.0"
    return SkillRegistration(
        skill_id=f"local/{name}@{version}",
        namespace="local",
        name=name,
        version=version,
        manifest_version="0.3",
        metadata=SkillMetadata(
            name=name,
            version=version,
            description=f"{name}测试能力",
            inputs=(),
            outputs=(),
            keywords=(name,),
        ),
        lifecycle_status=SkillLifecycleStatus.ACTIVE,
        health_status=HealthStatus.HEALTHY,
    )


class RecordingSkill:
    def __init__(self, name: str, calls: list[str], *, fail: bool = False) -> None:
        self.name = name
        self.calls = calls
        self.fail = fail
        self.contexts: list[TaskContext] = []

    def execute(self, context: TaskContext) -> str:
        self.calls.append(self.name)
        self.contexts.append(context)
        if self.fail:
            raise RuntimeError(f"{self.name}-failed")
        return f"{self.name}-output"


class TaskPlanExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = RuntimeManager()
        environment = self.runtime.create_environment("执行测试")
        self.task_id = environment.context.task_id
        self.calls: list[str] = []
        self.first = RecordingSkill("first", self.calls)
        self.second = RecordingSkill("second", self.calls)
        registrations = [make_registration("first"), make_registration("second")]
        registry = SkillRegistry()
        for registration in registrations:
            registry.register(registration)
        self.executor = TaskPlanExecutor(
            self.runtime,
            SkillRouter(registry),
            InMemorySkillResolver(
                {
                    registrations[0].skill_id: self.first,
                    registrations[1].skill_id: self.second,
                }
            ),
        )

    def make_plan(self) -> TaskPlan:
        return TaskPlan(
            plan_id="plan-001",
            task_id=self.task_id,
            created_at=datetime.now(timezone.utc),
            steps=(
                PlanStep(
                    step_id="step-1",
                    order=1,
                    skill_id="local/first@0.3.0",
                    input_schema={"type": "object"},
                    dependency=(),
                    expected_output={
                        "type": "object",
                        "properties": {"result": {"type": "string"}},
                    },
                ),
                PlanStep(
                    step_id="step-2",
                    order=2,
                    skill_id="local/second@0.3.0",
                    input_schema={"type": "object"},
                    dependency=("step-1",),
                    expected_output={
                        "type": "object",
                        "properties": {"result": {"type": "string"}},
                    },
                ),
            ),
        )

    def test_steps_execute_in_order_and_runtime_completes(self) -> None:
        result = self.executor.execute(self.make_plan())

        self.assertEqual(self.calls, ["first", "second"])
        self.assertTrue(result.success)
        self.assertEqual(
            list(result.outputs),
            ["step-1", "step-2"],
        )
        environment = self.runtime.get_environment(self.task_id)
        self.assertEqual(environment.lifecycle.status, LifecycleStatus.COMPLETED)
        self.assertEqual(
            environment.lifecycle.history,
            [
                LifecycleStatus.CREATED,
                LifecycleStatus.PLANNING,
                LifecycleStatus.EXECUTING,
                LifecycleStatus.COMPLETED,
            ],
        )
        first_context = self.first.contexts[0]
        second_context = self.second.contexts[0]
        assert first_context.invocation_context is not None
        assert second_context.invocation_context is not None
        self.assertEqual(
            first_context.invocation_context.skill_id,
            "local/first@0.3.0",
        )
        self.assertEqual(
            second_context.metadata["dependency_outputs"],
            {"step-1": "first-output"},
        )
        self.assertNotEqual(
            first_context.invocation_context.span_id,
            second_context.invocation_context.span_id,
        )

    def test_skill_failure_is_propagated_and_runtime_fails(self) -> None:
        self.second.fail = True

        with self.assertRaises(StepExecutionError) as captured:
            self.executor.execute(self.make_plan())

        self.assertEqual(captured.exception.step_id, "step-2")
        self.assertIsInstance(captured.exception.__cause__, RuntimeError)
        environment = self.runtime.get_environment(self.task_id)
        self.assertEqual(environment.lifecycle.status, LifecycleStatus.FAILED)
        self.assertEqual(self.calls, ["first", "second"])


if __name__ == "__main__":
    unittest.main()
