import pytest

from app.adapters.agent import (
    AgentAdapter,
    AgentInvocationError,
    AgentRequestConversionError,
    AgentResultConversionError,
)

from .helpers import make_message


class FailingRuntime:
    def invoke(self, task: object) -> object:
        raise TimeoutError("internal details")


class InvalidResultRuntime:
    def invoke(self, task: object) -> object:
        return object()


def test_invalid_gateway_request_is_rejected() -> None:
    with pytest.raises(AgentRequestConversionError):
        AgentAdapter(FailingRuntime()).invoke(object())  # type: ignore[arg-type]


def test_runtime_exception_is_converted() -> None:
    with pytest.raises(AgentInvocationError) as captured:
        AgentAdapter(FailingRuntime()).invoke(make_message())
    assert isinstance(captured.value.__cause__, TimeoutError)


def test_invalid_runtime_result_is_rejected() -> None:
    with pytest.raises(AgentResultConversionError):
        AgentAdapter(InvalidResultRuntime()).invoke(make_message())
