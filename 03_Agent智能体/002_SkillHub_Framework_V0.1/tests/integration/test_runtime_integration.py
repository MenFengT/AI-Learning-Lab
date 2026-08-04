import unittest
from typing import Any, Mapping

from app.core.agent import SkillHubAgent
from app.core.context import TaskContext
from app.core.skill_resolver import InMemorySkillResolver
from app.core.skill_router import SkillRouter
from app.registry import (
    HealthStatus,
    SkillLifecycleStatus,
    SkillMetadata,
    SkillRegistration,
    SkillRegistry,
    build_skill_id,
)
from app.runtime.invocation_context import InvocationContext
from app.runtime.lifecycle import LifecycleStatus
from app.runtime.runtime_manager import RuntimeManager
from app.services.audit.models import AuditEvent
from app.services.context import ServiceContext
from app.services.models import MCPRequest, MCPResponse
from app.skills.base_skill import BaseSkill


class ContextRecordingSkill(BaseSkill):
    name = "runtime_probe"
    description = "验证V0.2运行时上下文贯穿"
    keywords = ("运行时贯穿",)

    def __init__(self) -> None:
        self.received_context: TaskContext | None = None

    def execute(self, context: TaskContext) -> str:
        self.received_context = context
        return "integration-ok"


class FakeMCPClient:
    def call(self, request: MCPRequest) -> MCPResponse:
        raise AssertionError("本测试不执行MCP调用")


class FakeAuditService:
    def record(self, event: Mapping[str, Any]) -> None:
        return None


class FakeServiceConfig:
    default_timeout_seconds = 5.0
    max_timeout_seconds = 30.0


class RuntimeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.skill = ContextRecordingSkill()
        version = "0.2.0"
        self.skill_id = build_skill_id("local", self.skill.name, version)
        registration = SkillRegistration(
            skill_id=self.skill_id,
            namespace="local",
            name=self.skill.name,
            version=version,
            manifest_version="0.2",
            metadata=SkillMetadata(
                name=self.skill.name,
                version=version,
                description=self.skill.description,
                inputs=(),
                outputs=(),
                keywords=self.skill.keywords,
            ),
            lifecycle_status=SkillLifecycleStatus.ACTIVE,
            health_status=HealthStatus.HEALTHY,
        )
        registry = SkillRegistry()
        registry.register(registration)
        self.runtime = RuntimeManager()
        self.agent = SkillHubAgent(
            SkillRouter(registry),
            self.runtime,
            InMemorySkillResolver({self.skill_id: self.skill}),
        )

    def test_agent_runtime_registry_router_skill_chain(self) -> None:
        result = self.agent.run("请验证运行时贯穿", user_id="user-001")

        self.assertEqual(result, "integration-ok")
        self.assertIsNotNone(self.skill.received_context)
        task_context = self.skill.received_context
        assert task_context is not None
        invocation = task_context.invocation_context
        self.assertIsInstance(invocation, InvocationContext)
        assert invocation is not None

        environment = self.runtime.get_environment(invocation.task_id)
        self.assertEqual(invocation.task_id, environment.context.task_id)
        self.assertEqual(invocation.trace_id, environment.context.trace_id)
        self.assertNotEqual(invocation.span_id, environment.trace.span_id)
        self.assertEqual(invocation.skill_id, self.skill_id)
        self.assertEqual(invocation.user_id, "user-001")
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
        self.assertEqual(environment.context.outputs["result"], result)

    def test_task_context_legacy_constructor_remains_compatible(self) -> None:
        context = TaskContext(user_task="兼容任务")

        self.assertIsNone(context.invocation_context)
        self.assertEqual(context.user_task, "兼容任务")

    def test_invocation_context_supports_service_mcp_and_audit_contracts(self) -> None:
        self.agent.run("请验证运行时贯穿")
        task_context = self.skill.received_context
        assert task_context is not None
        invocation = task_context.invocation_context
        assert invocation is not None

        service_context = ServiceContext(
            mcp_client=FakeMCPClient(),
            audit_service=FakeAuditService(),
            runtime_context=invocation,
            config=FakeServiceConfig(),
        )
        request = MCPRequest(
            server_name="test-server",
            tool_name="test.call",
            arguments={"value": 1},
            runtime_context=invocation,
            timeout=5.0,
        )
        event = AuditEvent(
            task_id=invocation.task_id,
            trace_id=invocation.trace_id,
            span_id=invocation.span_id,
            skill_id=invocation.skill_id,
            server="test-server",
            tool="test.call",
            duration=0.1,
        )

        self.assertIs(service_context.runtime_context, invocation)
        self.assertIs(request.runtime_context, invocation)
        self.assertEqual(event.task_id, invocation.task_id)
        self.assertEqual(event.trace_id, invocation.trace_id)
        self.assertEqual(event.span_id, invocation.span_id)
        self.assertEqual(event.skill_id, invocation.skill_id)


if __name__ == "__main__":
    unittest.main()
