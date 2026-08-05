"""SkillHub 应用对象图工厂。"""

from dataclasses import dataclass
from typing import Callable, Mapping

from app.adapters.agent import AgentAdapter, AgentRuntimeInvocationProtocol
from app.adapters.telegram import (
    TelegramAdapter,
    TelegramAttachmentResolverProtocol,
)
from app.config.models import ApplicationConfig
from app.core.agent import SkillHubAgent
from app.core.skill_resolver import InMemorySkillResolver
from app.core.skill_router import SkillRouter
from app.execution.executor import TaskPlanExecutor
from app.gateway.service import InteractionGateway
from app.planner.planner import Planner
from app.planner.protocols import PlanDraftProviderProtocol
from app.registry.models import SkillRegistration
from app.registry.registry import SkillRegistry
from app.runtime.runtime_manager import RuntimeManager
from app.skills.base_skill import BaseSkill

from .container import ApplicationContainer
from .errors import CompositionError


AgentInvocationFactory = Callable[
    [SkillHubAgent, RuntimeManager, Planner, TaskPlanExecutor],
    AgentRuntimeInvocationProtocol,
]


@dataclass(frozen=True)
class ApplicationDependencies:
    """Composition Root 唯一外部输入；所有应用依赖均显式提供。"""

    skill_registrations: tuple[SkillRegistration, ...]
    skill_bindings: Mapping[str, BaseSkill]
    plan_draft_provider: PlanDraftProviderProtocol
    agent_invocation_factory: AgentInvocationFactory
    telegram_attachment_resolver: TelegramAttachmentResolverProtocol


class ApplicationFactory:
    """只创建并连接对象，不执行业务方法。"""

    def create(
        self,
        dependencies: ApplicationDependencies,
        application_config: ApplicationConfig | None = None,
    ) -> ApplicationContainer:
        if not isinstance(dependencies, ApplicationDependencies):
            raise CompositionError("dependencies必须是ApplicationDependencies")
        if application_config is not None and not isinstance(
            application_config, ApplicationConfig
        ):
            raise CompositionError(
                "application_config必须是ApplicationConfig或None"
            )

        runtime = RuntimeManager()
        registry = SkillRegistry()
        for registration in dependencies.skill_registrations:
            registry.register(registration)

        registration_ids = {item.skill_id for item in dependencies.skill_registrations}
        binding_ids = set(dependencies.skill_bindings)
        if registration_ids != binding_ids:
            raise CompositionError(
                "Skill Descriptor与实例绑定必须一一对应："
                f"registrations={sorted(registration_ids)}, bindings={sorted(binding_ids)}"
            )

        router = SkillRouter(registry)
        resolver = InMemorySkillResolver(dependencies.skill_bindings)
        planner = Planner(dependencies.plan_draft_provider)
        executor = TaskPlanExecutor(runtime, router, resolver)
        agent = SkillHubAgent(router, runtime, resolver)

        try:
            invocation = dependencies.agent_invocation_factory(
                agent, runtime, planner, executor
            )
        except Exception as exc:
            raise CompositionError("Agent Runtime调用端口创建失败") from exc
        if not isinstance(invocation, AgentRuntimeInvocationProtocol):
            raise CompositionError("Agent Runtime调用端口不满足Protocol")

        agent_adapter = AgentAdapter(invocation)
        gateway = InteractionGateway(agent_adapter)
        telegram = TelegramAdapter(
            gateway, dependencies.telegram_attachment_resolver
        )
        return ApplicationContainer(
            runtime_manager=runtime,
            skill_registry=registry,
            skill_router=router,
            skill_resolver=resolver,
            planner=planner,
            task_plan_executor=executor,
            agent=agent,
            agent_runtime_invocation=invocation,
            agent_adapter=agent_adapter,
            gateway=gateway,
            telegram_adapter=telegram,
            application_config=application_config,
        )
