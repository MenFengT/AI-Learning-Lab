from app.adapters.agent import AgentAdapter

from .helpers import FakeAgentRuntime, make_message


def test_agent_runtime_is_called_once() -> None:
    runtime = FakeAgentRuntime()

    AgentAdapter(runtime).invoke(make_message())

    assert len(runtime.calls) == 1
