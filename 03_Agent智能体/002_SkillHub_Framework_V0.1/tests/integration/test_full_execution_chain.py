import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping

from app.core.agent import SkillHubAgent
from app.core.context import TaskContext
from app.core.skill_resolver import InMemorySkillResolver
from app.core.skill_router import SkillRouter
from app.knowledge import KnowledgeRouter
from app.mcp_registry import (
    MCPServerDescriptor,
    MCPServerRegistry,
    ServerCapabilities,
    ServerHealthStatus,
    ToolDescriptor,
    ToolIdempotency,
    TransportType,
    build_server_id,
)
from app.mcp_servers.knowledge import KnowledgeMCPServerAdapter
from app.mcp_servers.permissions import InMemoryMCPServerPermissionPolicy
from app.registry import (
    HealthStatus,
    SkillLifecycleStatus,
    SkillMetadata,
    SkillRegistration,
    SkillRegistry,
    build_skill_id,
)
from app.runtime.lifecycle import LifecycleStatus
from app.runtime.runtime_manager import RuntimeManager
from app.services.audit import InMemoryAuditService
from app.services.governance import (
    AuditPolicy,
    CircuitCallPolicy,
    GovernanceConfig,
    Idempotency,
    OperationType,
    ServiceCallExecutor,
    ServiceCallPolicy,
)
from app.services.knowledge import (
    KnowledgeAccessPolicy,
    KnowledgeDocumentRequest,
    KnowledgePermission,
    KnowledgeQueryRequest,
    KnowledgeRuntimeContext,
    KnowledgeService,
)
from app.services.mcp import ConnectionManager, MCPClient, ServerConfig
from app.services.resilience import (
    CircuitBreaker,
    CircuitBreakerPolicy,
    RetryExecutor,
    RetryPolicy,
    SystemClock,
)
from app.skills.base_skill import BaseSkill

from tests.knowledge.test_knowledge_router import build_roots


SKILL_ID = build_skill_id("local", "knowledge_probe", "0.2.0")


class KnowledgeAdapterTransport:
    def __init__(self, adapter: KnowledgeMCPServerAdapter) -> None:
        self._adapter = adapter
        self.connected = False
        self.last_payload: Mapping[str, Any] | None = None

    def connect(self, config: ServerConfig) -> None:
        self.connected = True

    def send(
        self, payload: Mapping[str, Any], timeout: float
    ) -> Mapping[str, Any]:
        self.last_payload = payload
        return self._adapter.handle(payload)

    def close(self) -> None:
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected


class RecordingTransportConfigProvider:
    def __init__(self, config: ServerConfig) -> None:
        self._config = config
        self.references: list[str] = []

    def resolve(self, transport_config_reference: str) -> ServerConfig:
        self.references.append(transport_config_reference)
        return self._config


class KnowledgeProbeSkill(BaseSkill):
    name = "knowledge_probe"
    description = "验证Foundation完整执行链"
    keywords = ("知识链路",)

    def __init__(self, service: KnowledgeService) -> None:
        self._service = service
        self.received_context: TaskContext | None = None

    def execute(self, context: TaskContext) -> str:
        self.received_context = context
        invocation = context.invocation_context
        if invocation is None:
            raise RuntimeError("缺少InvocationContext")
        runtime = KnowledgeRuntimeContext(
            task_id=invocation.task_id,
            trace_id=invocation.trace_id,
            span_id=invocation.span_id,
            skill_id=invocation.skill_id,
            user_id=invocation.user_id,
            metadata=invocation.metadata,
        )
        if "失败" in context.user_task:
            result = self._service.get_document(
                KnowledgeDocumentRequest(runtime, "domain.missing", 5.0)
            )
            return result.error_code or "unexpected-success"
        result = self._service.query(
            KnowledgeQueryRequest(runtime, "混凝土", 5.0)
        )
        if not result.success:
            raise RuntimeError(result.error_code or "knowledge-call-failed")
        return result.data.domain_results[0].source.document_id


class FullExecutionChainTests(unittest.TestCase):
    def test_success_chain_preserves_context_and_audit_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._build(Path(directory))
            result = fixture["agent"].run(
                "请验证知识链路", user_id="user-foundation"
            )

        self.assertEqual(result, "domain.concrete")
        self._assert_chain(fixture, "SERVICE_CALL_SUCCEEDED")
        skill = fixture["skill"]
        invocation = skill.received_context.invocation_context
        environment = fixture["runtime"].get_environment(invocation.task_id)
        self.assertEqual(environment.lifecycle.status, LifecycleStatus.COMPLETED)

    def test_failed_service_call_emits_failed_audit_with_same_lineage(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._build(Path(directory))
            result = fixture["agent"].run("知识链路失败")

        self.assertEqual(result, "SHF-SVC-KNOWLEDGE-NOT_FOUND")
        self._assert_chain(fixture, "SERVICE_CALL_FAILED")

    def _assert_chain(
        self, fixture: dict[str, Any], terminal_event: str
    ) -> None:
        skill = fixture["skill"]
        context = skill.received_context
        self.assertIsNotNone(context)
        invocation = context.invocation_context
        self.assertIsNotNone(invocation)
        payload_context = fixture["transport"].last_payload["params"]["_meta"]
        events = fixture["audit"].events()

        self.assertEqual(
            [event.metadata["event_type"] for event in events],
            ["SERVICE_CALL_STARTED", terminal_event],
        )
        self.assertEqual(fixture["provider"].references, ["mcp.knowledge.v0_2"])
        self.assertEqual(
            fixture["server_registry"].get("knowledge-server").server_id,
            "knowledge-server@0.2.0",
        )
        for event in events:
            self.assertEqual(event.task_id, invocation.task_id)
            self.assertEqual(event.trace_id, invocation.trace_id)
            self.assertEqual(event.skill_id, SKILL_ID)
            self.assertEqual(event.span_id, payload_context["span_id"])
            self.assertEqual(
                event.metadata["parent_span_id"], invocation.span_id
            )
        self.assertEqual(payload_context["task_id"], invocation.task_id)
        self.assertEqual(payload_context["trace_id"], invocation.trace_id)
        self.assertEqual(payload_context["skill_id"], SKILL_ID)

    @staticmethod
    def _build(root: Path) -> dict[str, Any]:
        domain, standards = build_roots(root)
        server_permissions = InMemoryMCPServerPermissionPolicy(
            {
                SKILL_ID: frozenset(
                    {
                        "KNOWLEDGE_READ",
                        "STANDARDS_READ",
                        "KNOWLEDGE_DOCUMENT_READ",
                    }
                )
            }
        )
        adapter = KnowledgeMCPServerAdapter(
            KnowledgeRouter(domain, standards), server_permissions
        )
        transport = KnowledgeAdapterTransport(adapter)
        connection_manager = ConnectionManager(
            {"adapter": lambda: transport}
        )
        server_registry = MCPServerRegistry()
        tools = tuple(
            ToolDescriptor(
                tool_name=name,
                description=f"Fixed {name}",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                permission_required="KNOWLEDGE_READ",
                idempotency=ToolIdempotency.IDEMPOTENT,
            )
            for name in sorted(KnowledgeMCPServerAdapter.ALLOWED_TOOLS)
        )
        server_registry.register(
            MCPServerDescriptor(
                server_id=build_server_id("knowledge-server", "0.2.0"),
                server_name="knowledge-server",
                version="0.2.0",
                description="Knowledge MCP Server",
                transport_type=TransportType.IN_MEMORY,
                transport_config_reference="mcp.knowledge.v0_2",
                capabilities=ServerCapabilities(tools=True),
                allowed_tools=tools,
                health_status=ServerHealthStatus.HEALTHY,
            )
        )
        provider = RecordingTransportConfigProvider(
            ServerConfig(
                server_name="knowledge-server",
                transport_name="adapter",
                allowed_tools=KnowledgeMCPServerAdapter.ALLOWED_TOOLS,
                connect_timeout=1.0,
                max_request_timeout=5.0,
            )
        )
        mcp_client = MCPClient(
            server_registry, provider, connection_manager
        )
        clock = SystemClock()
        audit = InMemoryAuditService()
        executor = ServiceCallExecutor(
            mcp_client=mcp_client,
            audit_service=audit,
            retry_executor=RetryExecutor(clock),
            circuit_breaker=CircuitBreaker(
                CircuitBreakerPolicy(2, 10.0), clock
            ),
            clock=clock,
            config=GovernanceConfig(),
        )
        policy = ServiceCallPolicy(
            operation_type=OperationType.READ,
            idempotency=Idempotency.IDEMPOTENT,
            retry_policy=RetryPolicy(
                max_attempts=1,
                initial_delay_seconds=0,
                max_delay_seconds=0,
                backoff_multiplier=1,
                retryable_error_codes=frozenset(),
            ),
            circuit_policy=CircuitCallPolicy(),
            audit_policy=AuditPolicy(),
            timeout_budget=5.0,
        )
        service = KnowledgeService(
            executor,
            KnowledgeAccessPolicy(
                {
                    SKILL_ID: frozenset(
                        {
                            KnowledgePermission.KNOWLEDGE_READ,
                            KnowledgePermission.STANDARDS_READ,
                            KnowledgePermission.KNOWLEDGE_DOCUMENT_READ,
                        }
                    )
                }
            ),
            policy,
        )
        skill = KnowledgeProbeSkill(service)
        skill_registry = SkillRegistry()
        skill_registry.register(
            SkillRegistration(
                skill_id=SKILL_ID,
                namespace="local",
                name=skill.name,
                version="0.2.0",
                manifest_version="0.2",
                metadata=SkillMetadata(
                    name=skill.name,
                    version="0.2.0",
                    description=skill.description,
                    inputs=(),
                    outputs=(),
                    keywords=skill.keywords,
                ),
                lifecycle_status=SkillLifecycleStatus.ACTIVE,
                health_status=HealthStatus.HEALTHY,
            )
        )
        runtime = RuntimeManager()
        agent = SkillHubAgent(
            SkillRouter(skill_registry),
            runtime,
            InMemorySkillResolver({SKILL_ID: skill}),
        )
        return {
            "agent": agent,
            "audit": audit,
            "provider": provider,
            "runtime": runtime,
            "server_registry": server_registry,
            "skill": skill,
            "transport": transport,
        }


if __name__ == "__main__":
    unittest.main()
