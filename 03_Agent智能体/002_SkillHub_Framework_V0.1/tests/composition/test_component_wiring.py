from app.adapters.agent import AgentAdapter
from app.adapters.telegram import TelegramAdapter
from app.composition import bootstrap
from app.core.agent import SkillHubAgent
from app.core.skill_router import SkillRouter
from app.execution.executor import TaskPlanExecutor
from app.gateway.service import InteractionGateway
from app.planner.planner import Planner
from app.registry.registry import SkillRegistry
from app.runtime.runtime_manager import RuntimeManager

from .helpers import RecordingInvocationFactory, dependencies


def test_all_required_components_are_wired() -> None:
    invocation_factory = RecordingInvocationFactory()
    container = bootstrap(dependencies(invocation_factory))

    assert isinstance(container.runtime_manager, RuntimeManager)
    assert isinstance(container.skill_registry, SkillRegistry)
    assert isinstance(container.skill_router, SkillRouter)
    assert isinstance(container.planner, Planner)
    assert isinstance(container.task_plan_executor, TaskPlanExecutor)
    assert isinstance(container.agent, SkillHubAgent)
    assert isinstance(container.agent_adapter, AgentAdapter)
    assert isinstance(container.gateway, InteractionGateway)
    assert isinstance(container.telegram_adapter, TelegramAdapter)
    assert invocation_factory.calls == [
        (
            container.agent,
            container.runtime_manager,
            container.planner,
            container.task_plan_executor,
        )
    ]


def test_bootstrap_creates_independent_object_graphs() -> None:
    left = bootstrap(dependencies())
    right = bootstrap(dependencies())
    assert left is not right
    assert left.runtime_manager is not right.runtime_manager
    assert left.skill_registry is not right.skill_registry
