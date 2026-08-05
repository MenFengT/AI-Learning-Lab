import unittest
from datetime import datetime, timezone

from app.planner import (
    PlanGenerationError,
    PlanStep,
    Planner,
    PlannerProtocol,
    UserRequest,
)


SCHEMA = {"type": "object", "properties": {}}


class FixedProvider:
    def __init__(self) -> None:
        self.calls = 0

    def generate_steps(self, request: UserRequest) -> tuple[PlanStep, ...]:
        self.calls += 1
        return (
            PlanStep(
                step_id="step-1",
                order=1,
                skill_id="local/example@0.3.0",
                input_schema=SCHEMA,
                dependency=(),
                expected_output=SCHEMA,
            ),
        )


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 8, 4, tzinfo=timezone.utc)


class FixedIdFactory:
    def create(self) -> str:
        return "plan-fixed"


class PlannerContractTests(unittest.TestCase):
    def test_planner_only_creates_validated_plan(self) -> None:
        provider = FixedProvider()
        planner = Planner(
            provider,
            clock=FixedClock(),
            id_factory=FixedIdFactory(),
        )
        request = UserRequest("task-001", "生成任务计划")

        plan = planner.create_plan(request)

        self.assertIsInstance(planner, PlannerProtocol)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(plan.plan_id, "plan-fixed")
        self.assertEqual(plan.task_id, request.task_id)
        self.assertEqual(plan.steps[0].skill_id, "local/example@0.3.0")
        self.assertFalse(hasattr(planner, "execute"))

    def test_provider_failure_is_converted_without_execution(self) -> None:
        class FailingProvider:
            def generate_steps(self, request: UserRequest) -> tuple[PlanStep, ...]:
                raise RuntimeError("provider internal detail")

        planner = Planner(FailingProvider())

        with self.assertRaises(PlanGenerationError) as raised:
            planner.create_plan(UserRequest("task-001", "生成任务计划"))

        self.assertNotIn("internal detail", str(raised.exception))

    def test_planner_rejects_non_request_input(self) -> None:
        with self.assertRaises(PlanGenerationError):
            Planner(FixedProvider()).create_plan("raw user input")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
