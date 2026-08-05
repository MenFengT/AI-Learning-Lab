from app.adapters.agent import (
    AgentGatewayAdapterProtocol,
    AgentRuntimeInvocationProtocol,
)
from app.adapters.telegram import TelegramGatewayAdapterProtocol
from app.gateway.protocols import AgentInvocationProtocol, InteractionGatewayProtocol
from app.planner.protocols import PlannerProtocol

from app.composition import bootstrap

from .helpers import dependencies


def test_wired_components_satisfy_public_protocols() -> None:
    container = bootstrap(dependencies())
    assert isinstance(container.planner, PlannerProtocol)
    assert callable(container.task_plan_executor.execute)
    assert isinstance(container.agent_runtime_invocation, AgentRuntimeInvocationProtocol)
    assert isinstance(container.agent_adapter, AgentGatewayAdapterProtocol)
    assert isinstance(container.agent_adapter, AgentInvocationProtocol)
    assert isinstance(container.gateway, InteractionGatewayProtocol)
    assert isinstance(container.telegram_adapter, TelegramGatewayAdapterProtocol)
