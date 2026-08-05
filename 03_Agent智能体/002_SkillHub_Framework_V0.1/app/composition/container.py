"""应用组件只读容器；不提供动态查找或Service Locator。"""

from dataclasses import dataclass

from app.adapters.agent import AgentAdapter, AgentRuntimeInvocationProtocol
from app.adapters.telegram import TelegramAdapter
from app.config.models import ApplicationConfig
from app.core.agent import SkillHubAgent
from app.core.skill_resolver import InMemorySkillResolver
from app.core.skill_router import SkillRouter
from app.execution.executor import TaskPlanExecutor
from app.gateway.service import InteractionGateway
from app.planner.planner import Planner
from app.registry.registry import SkillRegistry
from app.runtime.runtime_manager import RuntimeManager


@dataclass(frozen=True)
class ApplicationContainer:
    """显式声明可用组件，禁止按字符串进行依赖定位。"""

    runtime_manager: RuntimeManager
    skill_registry: SkillRegistry
    skill_router: SkillRouter
    skill_resolver: InMemorySkillResolver
    planner: Planner
    task_plan_executor: TaskPlanExecutor
    agent: SkillHubAgent
    agent_runtime_invocation: AgentRuntimeInvocationProtocol
    agent_adapter: AgentAdapter
    gateway: InteractionGateway
    telegram_adapter: TelegramAdapter
    application_config: ApplicationConfig | None = None
