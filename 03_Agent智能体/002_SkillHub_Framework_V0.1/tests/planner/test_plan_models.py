import unittest
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone

from app.planner import PlanStep, PlanStepStatus, TaskPlan, UserRequest


def schema(field_name: str = "value") -> dict[str, object]:
    return {
        "type": "object",
        "properties": {field_name: {"type": "string"}},
        "required": [field_name],
    }


def step() -> PlanStep:
    return PlanStep(
        step_id="step-1",
        order=1,
        skill_id="local/example@0.3.0",
        input_schema=schema("request"),
        dependency=(),
        expected_output=schema("result"),
    )


class PlanModelTests(unittest.TestCase):
    def test_task_plan_contract_and_default_status(self) -> None:
        plan = TaskPlan(
            plan_id="plan-001",
            task_id="task-001",
            created_at=datetime(2026, 8, 4, tzinfo=timezone.utc),
            steps=(step(),),
            metadata={"source": "test"},
        )

        self.assertEqual(plan.steps[0].status, PlanStepStatus.PENDING)
        self.assertEqual(
            {item.name for item in fields(PlanStep)},
            {
                "step_id",
                "order",
                "skill_id",
                "input_schema",
                "dependency",
                "expected_output",
                "status",
            },
        )
        with self.assertRaises(FrozenInstanceError):
            plan.plan_id = "changed"  # type: ignore[misc]

    def test_nested_inputs_and_schemas_are_isolated(self) -> None:
        inputs = {"files": [{"file_id": "file-1"}]}
        input_schema = schema("request")
        request = UserRequest(
            task_id="task-001",
            user_request="创建计划",
            inputs=inputs,
        )
        plan_step = PlanStep(
            step_id="step-1",
            order=1,
            skill_id="local/example@0.3.0",
            input_schema=input_schema,
            dependency=(),
            expected_output=schema("result"),
        )

        inputs["files"][0]["file_id"] = "polluted"
        input_schema["properties"]["request"]["type"] = "integer"

        self.assertEqual(request.inputs["files"][0]["file_id"], "file-1")
        self.assertEqual(
            plan_step.input_schema["properties"]["request"]["type"],
            "string",
        )

    def test_models_reject_executable_and_unstable_skill_identity(self) -> None:
        with self.assertRaisesRegex(ValueError, "可执行对象"):
            UserRequest(
                task_id="task-001",
                user_request="创建计划",
                inputs={"callback": lambda: None},
            )
        with self.assertRaisesRegex(ValueError, "skill_id"):
            PlanStep(
                step_id="step-1",
                order=1,
                skill_id="random-skill-id",
                input_schema=schema(),
                dependency=(),
                expected_output=schema("result"),
            )


if __name__ == "__main__":
    unittest.main()
