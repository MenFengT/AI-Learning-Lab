import unittest

from app.core.context import TaskContext
from app.runtime.execution_context import ExecutionContext
from app.runtime.lifecycle import LifecycleStatus
from app.runtime.runtime_manager import ExtensionLevel, RuntimeManager
from app.runtime.trace import Trace, generate_trace_id


class RecordingExtension:
    def __init__(self) -> None:
        self.events: list[tuple[str, LifecycleStatus, LifecycleStatus]] = []

    def on_status_change(
        self,
        context: ExecutionContext,
        previous_status: LifecycleStatus,
        current_status: LifecycleStatus,
    ) -> None:
        self.events.append((context.task_id, previous_status, current_status))


class FailingExtension:
    def on_status_change(
        self,
        context: ExecutionContext,
        previous_status: LifecycleStatus,
        current_status: LifecycleStatus,
    ) -> None:
        raise RuntimeError("extension unavailable")


class RuntimeTests(unittest.TestCase):
    def test_trace_and_span_relationship(self) -> None:
        first_id = generate_trace_id()
        second_id = generate_trace_id()
        self.assertNotEqual(first_id, second_id)

        root = Trace.create()
        child = root.create_child()
        sibling = root.create_child()
        self.assertEqual(root.trace_id, child.trace_id)
        self.assertEqual(root.trace_id, sibling.trace_id)
        self.assertNotEqual(root.span_id, child.span_id)
        self.assertNotEqual(child.span_id, sibling.span_id)
        self.assertEqual(child.parent_span_id, root.span_id)

    def test_create_environment_builds_isolated_context(self) -> None:
        source_inputs = {"file": "plan.xlsx"}
        source_metadata = {"source": "test"}
        manager = RuntimeManager()

        environment = manager.create_environment(
            "生成材料计划",
            user_id="user-001",
            inputs=source_inputs,
            metadata=source_metadata,
        )
        source_inputs["file"] = "changed.xlsx"
        source_metadata["source"] = "changed"

        self.assertEqual(environment.context.user_request, "生成材料计划")
        self.assertEqual(environment.context.user_id, "user-001")
        self.assertEqual(environment.context.inputs["file"], "plan.xlsx")
        self.assertEqual(environment.context.metadata["source"], "test")
        self.assertEqual(environment.context.trace_id, environment.trace.trace_id)
        self.assertEqual(environment.context.schema_version, "0.1")
        self.assertEqual(environment.lifecycle.status, LifecycleStatus.CREATED)
        self.assertIs(
            manager.get_environment(environment.context.task_id), environment
        )

    def test_context_deeply_isolates_mutable_inputs(self) -> None:
        source_inputs = {"documents": [{"pages": [1, 2]}]}
        source_metadata = {"source": {"tags": ["original"]}}
        manager = RuntimeManager()

        environment = manager.create_environment(
            "process documents",
            inputs=source_inputs,
            metadata=source_metadata,
        )
        source_inputs["documents"][0]["pages"].append(3)
        source_metadata["source"]["tags"].append("changed")

        self.assertEqual(
            environment.context.inputs, {"documents": [{"pages": [1, 2]}]}
        )
        self.assertEqual(
            environment.context.metadata, {"source": {"tags": ["original"]}}
        )

    def test_non_blocking_extension_failure_is_recorded(self) -> None:
        manager = RuntimeManager()
        manager.register_extension(
            FailingExtension(), ExtensionLevel.NON_BLOCKING
        )
        environment = manager.create_environment("execute task")

        manager.transition(
            environment.context.task_id, LifecycleStatus.PLANNING
        )

        self.assertEqual(environment.lifecycle.status, LifecycleStatus.PLANNING)
        errors = environment.context.metadata["extension_errors"]
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["extension_name"], "FailingExtension")
        self.assertEqual(errors[0]["error_type"], "RuntimeError")

    def test_blocking_extension_failure_is_propagated(self) -> None:
        manager = RuntimeManager()
        manager.register_extension(FailingExtension())
        environment = manager.create_environment("execute task")

        with self.assertRaisesRegex(RuntimeError, "extension unavailable"):
            manager.transition(
                environment.context.task_id, LifecycleStatus.PLANNING
            )

    def test_complete_lifecycle_and_extension_events(self) -> None:
        manager = RuntimeManager()
        extension = RecordingExtension()
        manager.register_extension(extension)
        environment = manager.create_environment("执行任务")
        task_id = environment.context.task_id

        manager.transition(task_id, LifecycleStatus.PLANNING)
        manager.transition(task_id, LifecycleStatus.EXECUTING)
        manager.complete(task_id, {"result": "ok"})

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
        self.assertEqual(environment.context.outputs, {"result": "ok"})
        self.assertEqual(len(extension.events), 3)

    def test_invalid_transition_is_rejected(self) -> None:
        manager = RuntimeManager()
        environment = manager.create_environment("执行任务")
        with self.assertRaises(ValueError):
            manager.transition(
                environment.context.task_id, LifecycleStatus.COMPLETED
            )

    def test_fail_records_error_and_terminal_state(self) -> None:
        manager = RuntimeManager()
        environment = manager.create_environment("执行任务")

        manager.fail(environment.context.task_id, "依赖不可用")

        self.assertEqual(environment.lifecycle.status, LifecycleStatus.FAILED)
        self.assertEqual(environment.context.metadata["error"], "依赖不可用")
        with self.assertRaises(ValueError):
            manager.fail(environment.context.task_id, "再次失败")

    def test_empty_request_and_unknown_task_are_rejected(self) -> None:
        manager = RuntimeManager()
        with self.assertRaises(ValueError):
            manager.create_environment("   ")
        with self.assertRaises(KeyError):
            manager.get_environment("missing")

    def test_v01_task_context_remains_available(self) -> None:
        context = TaskContext(user_task="兼容任务")
        self.assertEqual(context.user_task, "兼容任务")


if __name__ == "__main__":
    unittest.main()
