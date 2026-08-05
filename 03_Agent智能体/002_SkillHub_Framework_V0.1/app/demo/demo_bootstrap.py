"""MVP端到端Demo的确定性依赖实现与完整对象图装配。"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from app.adapters.agent import AgentTaskInput, AgentTaskResult
from app.adapters.telegram import TelegramAttachmentResolverProtocol
from app.artifact.models import Artifact
from app.artifact.service import ArtifactService
from app.composition import ApplicationContainer, ApplicationDependencies, bootstrap
from app.content.generator import ContentGenerator
from app.content.models import ContentPlan, ContentSection
from app.delivery import (
    ArtifactDeliveryReference,
    ArtifactDeliveryService,
    DeliveryReference,
    DeliveryRequest,
    DeliveryTarget,
    DeliveryTargetType,
)
from app.gateway.models import AgentArtifactReference, AsyncTaskStatus
from app.mcp_servers.office import OfficeMCPServerAdapter
from app.mcp_servers.office.runtime import OfficeCLIAdapter, OfficeCLIRequest, OfficeCLIResult
from app.mcp_servers.permissions import InMemoryMCPServerPermissionPolicy
from app.planner.models import PlanStep, UserRequest
from app.registry.models import HealthStatus, SkillLifecycleStatus, SkillMetadata, SkillRegistration
from app.runtime.invocation_context import InvocationContext
from app.services.audit.service import InMemoryAuditService
from app.services.content.service import ContentService
from app.services.filesystem.models import FileMetadata, FileReference, WorkspaceArea
from app.services.governance import AuditPolicy, CircuitCallPolicy, GovernanceConfig, Idempotency, OperationType, ServiceCallExecutor, ServiceCallPolicy
from app.services.mcp.adapters.legacy_server_config_catalog import LegacyServerConfigCatalogAdapter
from app.services.mcp.client import MCPClient
from app.services.mcp.connection_manager import ConnectionManager
from app.services.mcp.models import ServerConfig
from app.services.office.service import OfficeService
from app.services.resilience import CircuitBreaker, CircuitBreakerPolicy, RetryExecutor, RetryPolicy, SystemClock
from app.skills.document.skill import DocumentSkill


DOCUMENT_SKILL_ID = "local/document_automation@0.3.0"


class DemoPlanDraftProvider:
    def generate_steps(self, request: UserRequest) -> tuple[PlanStep, ...]:
        return (
            PlanStep(
                step_id="create-report",
                order=1,
                skill_id=DOCUMENT_SKILL_ID,
                input_schema={
                    "type": "object",
                    "properties": {
                        "document_type": {"type": "string"},
                        "title": {"type": "string"},
                        "output_name": {"type": "string"},
                        "requirements": {"type": "string"},
                        "sections": {"type": "array"},
                    },
                    "required": (
                        "document_type", "title", "output_name", "requirements"
                    ),
                },
                dependency=(),
                expected_output={
                    "type": "object",
                    "properties": {"artifact_id": {"type": "string"}},
                    "required": ("artifact_id",),
                },
            ),
        )


class DemoContentPlanner:
    def plan(self, request) -> ContentPlan:
        sections = (
            ContentSection("overview", "项目概况", 1, "说明项目基本情况"),
            ContentSection("preparation", "开工准备", 2, "说明开工准备情况"),
            ContentSection("plan", "实施计划", 3, "说明后续实施安排"),
        )
        return ContentPlan("report", sections, tuple(item.section_id for item in sections), ())


class DemoTextProvider:
    def generate(self, section, context):
        return (f"{section.title}：围绕“{context.requirements}”形成的示例内容。",)


class UnusedKnowledgeService:
    def query(self, request):
        raise AssertionError("Demo内容计划不要求知识查询")


class NoopFileSystemService:
    """ArtifactService构造依赖；Demo中Artifact层不会调用它。"""


class DemoOfficeCLIRuntime:
    """实现真实OfficeCLI端口的确定性替身，不写磁盘。"""

    def __init__(self) -> None:
        self.requests: list[OfficeCLIRequest] = []

    def create_document(self, request: OfficeCLIRequest) -> OfficeCLIResult:
        self.requests.append(request)
        now = datetime.now(timezone.utc)
        output_name = str(request.arguments["output_name"])
        reference = FileReference(
            file_id=f"file-{request.task_id}",
            version="1",
            checksum="d" * 64,
            area=WorkspaceArea.OUTPUT,
            relative_path=f"output/{request.task_id}/{output_name}",
            metadata=FileMetadata(
                size=512,
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                created_at=now,
                updated_at=now,
            ),
            created_at=now,
            updated_at=now,
        )
        return OfficeCLIResult(reference, "docx", {"runtime": "demo-office-cli"})

    update_document = create_document
    convert_document = create_document
    export_document = create_document


class LocalOfficeTransport:
    """将MCP协议载荷交给本地Office MCP Server，不绕过MCPClient。"""

    def __init__(self, server: OfficeMCPServerAdapter) -> None:
        self._server = server
        self._connected = False

    def connect(self, config: ServerConfig) -> None:
        self._connected = True

    def send(self, payload: Mapping[str, Any], timeout: float) -> Mapping[str, Any]:
        if not self._connected:
            raise RuntimeError("transport未连接")
        return self._server.handle(payload)

    def close(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected


class DemoArtifactCatalog:
    def __init__(self, service: ArtifactService) -> None:
        self._service = service

    def get_reference(self, artifact_id: str, context: InvocationContext) -> ArtifactDeliveryReference:
        artifact = self._service.get(context, artifact_id)
        return ArtifactDeliveryReference(artifact.artifact_id, artifact.task_id, artifact.version, artifact.name)


class DemoDeliveryPolicy:
    def allows(self, artifact, target, context) -> bool:
        return artifact.task_id == context.task_id


class DemoDeliveryTransport:
    def __init__(self) -> None:
        self.deliveries = []

    def deliver(self, artifact, target, context) -> DeliveryReference:
        self.deliveries.append((artifact, target, context))
        return DeliveryReference(
            f"delivery-{context.task_id}", artifact.artifact_id,
            f"telegram://{target.recipient_reference}/{artifact.artifact_id}",
            target.target_type,
        )


class DemoAttachmentResolver:
    def resolve(self, attachment):
        raise ValueError("此Demo只接受文本消息")


class DemoAgentRuntimeInvocation:
    def __init__(self, agent, runtime, planner, executor, artifact_service, delivery_service) -> None:
        self._agent = agent
        self._runtime = runtime
        self._planner = planner
        self._executor = executor
        self._artifacts = artifact_service
        self._delivery = delivery_service

    def invoke(self, task: AgentTaskInput) -> AgentTaskResult:
        execution = self._agent.execute_plan(
            task.user_task, self._planner, self._executor,
            user_id=task.user_id,
            inputs={
                "create-report": {
                    "document_type": "report",
                    "title": "项目开工报告",
                    "output_name": "项目开工报告.docx",
                    "requirements": task.user_task,
                    "sections": (),
                }
            },
            metadata=task.metadata,
        )
        artifact_id = str(execution.outputs["create-report"])
        environment = self._runtime.get_environment(execution.task_id)
        step = execution.steps[0]
        context = InvocationContext(
            execution.task_id, environment.context.trace_id, step.span_id,
            step.skill_id, task.user_id,
        )
        artifact: Artifact = self._artifacts.get(context, artifact_id)
        target = DeliveryTarget(
            DeliveryTargetType.TELEGRAM,
            str(task.metadata.get("chat_id", "demo-chat")),
        )
        delivery = self._delivery.deliver(
            DeliveryRequest(artifact_id, execution.task_id, context, target)
        )
        return AgentTaskResult(
            task_id=execution.task_id,
            status=AsyncTaskStatus.COMPLETED,
            message="项目开工报告已生成并交付",
            artifacts=(AgentArtifactReference(artifact_id, artifact.version, artifact.artifact_type.value, artifact.name),),
            metadata={
                "trace_id": environment.context.trace_id,
                "span_id": step.span_id,
                "delivery_id": delivery.delivery_id,
                "external_reference": delivery.external_reference,
            },
        )


@dataclass(frozen=True)
class DemoApplication:
    container: ApplicationContainer
    audit_service: InMemoryAuditService
    office_cli_runtime: DemoOfficeCLIRuntime
    delivery_transport: DemoDeliveryTransport


def create_demo_application() -> DemoApplication:
    audit = InMemoryAuditService()
    clock = SystemClock()
    content = ContentService(
        DemoContentPlanner(), UnusedKnowledgeService(),
        ContentGenerator(DemoTextProvider()), audit, clock,
    )
    artifact_service = ArtifactService(NoopFileSystemService())
    office_runtime = DemoOfficeCLIRuntime()
    office_cli = OfficeCLIAdapter(office_runtime, audit)
    permissions = frozenset(definition.permission for definition in OfficeMCPServerAdapter.TOOL_DEFINITIONS)
    office_server = OfficeMCPServerAdapter(
        office_cli,
        InMemoryMCPServerPermissionPolicy({DOCUMENT_SKILL_ID: permissions}),
    )
    tools = frozenset(OfficeMCPServerAdapter.ALLOWED_TOOLS)
    config = ServerConfig("office-server", "in_memory", tools, 1.0, 30.0)
    catalog = LegacyServerConfigCatalogAdapter({"office-server": config})
    client = MCPClient(
        catalog, catalog,
        ConnectionManager({"in_memory": lambda: LocalOfficeTransport(office_server)}),
    )
    governance = ServiceCallExecutor(
        client, audit, RetryExecutor(clock),
        CircuitBreaker(CircuitBreakerPolicy(3, 10.0), clock),
        clock, GovernanceConfig(),
    )
    retry = RetryPolicy(1, 0.0, 0.0, 1.0, frozenset())
    policy = ServiceCallPolicy(
        OperationType.WRITE, Idempotency.IDEMPOTENT_WITH_KEY, retry,
        CircuitCallPolicy(), AuditPolicy(), 30.0,
    )
    office = OfficeService(governance, {name: policy for name in OfficeService.TOOLS})
    document_skill = DocumentSkill(content, artifact_service, office)
    delivery_transport = DemoDeliveryTransport()
    delivery = ArtifactDeliveryService(
        DemoArtifactCatalog(artifact_service), delivery_transport, DemoDeliveryPolicy()
    )

    registration = SkillRegistration(
        DOCUMENT_SKILL_ID, "local", "document_automation", "0.3.0", "0.1",
        SkillMetadata(
            "document_automation", "0.3.0", "生成结构化文档",
            (), (), frozenset(permissions), ("报告", "文档"),
        ),
        SkillLifecycleStatus.ACTIVE, HealthStatus.HEALTHY,
    )

    def invocation_factory(agent, runtime, planner, executor):
        return DemoAgentRuntimeInvocation(
            agent, runtime, planner, executor, artifact_service, delivery
        )

    container = bootstrap(
        ApplicationDependencies(
            (registration,), {DOCUMENT_SKILL_ID: document_skill},
            DemoPlanDraftProvider(), invocation_factory, DemoAttachmentResolver(),
        )
    )
    return DemoApplication(container, audit, office_runtime, delivery_transport)
