from app.adapters.agent import AgentAdapter
from app.gateway.models import AgentInvocationResult, AsyncTaskStatus

from .helpers import FakeAgentRuntime, make_message


def test_agent_result_is_converted_to_gateway_result() -> None:
    result = AgentAdapter(FakeAgentRuntime()).invoke(make_message())

    assert isinstance(result, AgentInvocationResult)
    assert result.task_id == "task-001"
    assert result.status is AsyncTaskStatus.COMPLETED
    assert result.message == "完成"
    assert result.artifacts[0].artifact_id == "artifact-001"
    assert result.metadata["trace_id"] == "trace-001"
