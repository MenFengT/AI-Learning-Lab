from app.composition import bootstrap
from app.runtime.lifecycle import LifecycleStatus

from .helpers import dependencies


def test_runtime_context_can_flow_through_wired_runtime() -> None:
    container = bootstrap(dependencies())
    environment = container.runtime_manager.create_environment(
        "生成报告", user_id="user-001"
    )
    container.runtime_manager.transition(
        environment.context.task_id, LifecycleStatus.PLANNING
    )
    invocation = container.runtime_manager.create_invocation_context(
        environment.context.task_id,
        "local/document_automation@0.3.0",
    )
    assert invocation.task_id == environment.context.task_id
    assert invocation.trace_id == environment.context.trace_id
    assert invocation.span_id
    assert invocation.skill_id == "local/document_automation@0.3.0"
    assert invocation.user_id == "user-001"
