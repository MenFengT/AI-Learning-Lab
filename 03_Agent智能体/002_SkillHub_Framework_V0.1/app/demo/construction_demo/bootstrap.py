"""施工文档闭环所需依赖的显式装配。"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from app.artifact.service import ArtifactService
from app.content.generator import ContentGenerator
from app.content.models import ContentPlan, ContentSection
from app.knowledge import KnowledgeRouter
from app.mcp_servers.knowledge import KnowledgeMCPServerAdapter
from app.mcp_servers.office import OfficeMCPServerAdapter
from app.mcp_servers.office.runtime import (
    OfficeCLIAdapter,
    OfficeCLIRequest,
    OfficeCLIResult,
)
from app.mcp_servers.office.runtime.protocols import OfficeCLIRuntimeProtocol
from app.mcp_servers.permissions import InMemoryMCPServerPermissionPolicy
from app.services.audit.service import InMemoryAuditService
from app.services.content.service import ContentService
from app.services.filesystem.models import (
    FileMetadata,
    FileReference,
    WorkspaceArea,
)
from app.services.governance import (
    AuditPolicy,
    CircuitCallPolicy,
    GovernanceConfig,
    Idempotency,
    OperationType,
    ServiceCallExecutor,
    ServiceCallPolicy,
)
from app.services.knowledge.permissions import (
    KnowledgeAccessPolicy,
    KnowledgePermission,
)
from app.services.knowledge.service import KnowledgeService
from app.services.mcp.adapters.legacy_server_config_catalog import (
    LegacyServerConfigCatalogAdapter,
)
from app.services.mcp.client import MCPClient
from app.services.mcp.connection_manager import ConnectionManager
from app.services.mcp.models import ServerConfig
from app.services.office.service import OfficeService
from app.services.resilience import (
    CircuitBreaker,
    CircuitBreakerPolicy,
    RetryExecutor,
    RetryPolicy,
    SystemClock,
)
from app.skills.construction import (
    ConstructionDocumentSkill,
    PackageConstructionTemplateProvider,
)


CONSTRUCTION_SKILL_ID = "local/construction_document@0.1.0"


class ConstructionContentPlanner:
    """按 ConstructionSkill 已选择的模板章节建立内容计划。"""

    def plan(self, request) -> ContentPlan:
        sections = tuple(
            ContentSection(
                section_id=section_id,
                title=section_id.replace("_", " "),
                order=order,
                instructions="结合施工知识片段形成可执行章节内容",
            )
            for order, section_id in enumerate(request.requested_sections, 1)
        )
        return ContentPlan(
            document_type=request.document_type,
            sections=sections,
            section_order=tuple(item.section_id for item in sections),
            required_knowledge=(),
            metadata=request.metadata,
        )


class ConstructionTextProvider:
    def generate(self, section, context):
        fragments = tuple(context.metadata.get("knowledge_fragments", ()))
        evidence = fragments[0] if fragments else "未提供知识片段"
        summary = " ".join(str(evidence).split())[:240]
        return (
            f"{section.title}：{context.requirements}。参考施工知识：{summary}",
        )


class ObservedKnowledgeService:
    def __init__(self, service: KnowledgeService) -> None:
        self._service = service
        self.document_ids: tuple[str, ...] = ()

    def query(self, request):
        result = self._service.query(request)
        if result.success and result.data is not None:
            hits = (*result.data.domain_results, *result.data.standards_results)
            self.document_ids = tuple(hit.source.document_id for hit in hits)
        return result


class NoopFileSystemService:
    """ArtifactService仅保存FileReference，本流程不直接访问文件。"""


class ConstructionOfficeRuntime:
    """确定性OfficeCLI端口实现；不写磁盘、不接受路径。"""

    def __init__(self) -> None:
        self.requests: list[OfficeCLIRequest] = []

    def create_document(self, request: OfficeCLIRequest) -> OfficeCLIResult:
        self.requests.append(request)
        now = datetime.now(timezone.utc)
        output_name = str(request.arguments["output_name"])
        reference = FileReference(
            file_id=f"file-{request.task_id}",
            version="1",
            checksum="c" * 64,
            area=WorkspaceArea.OUTPUT,
            relative_path=f"output/{request.task_id}/{output_name}",
            metadata=FileMetadata(
                size=2048,
                content_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
                created_at=now,
                updated_at=now,
            ),
            created_at=now,
            updated_at=now,
        )
        return OfficeCLIResult(
            reference,
            "docx",
            {"runtime": "construction-demo-office-cli"},
        )

    update_document = create_document
    convert_document = create_document
    export_document = create_document


class LocalMCPTransport:
    """把协议载荷交给固定MCP Server Adapter。"""

    def __init__(self, server: Any) -> None:
        self._server = server
        self._connected = False

    def connect(self, config: ServerConfig) -> None:
        self._connected = True

    def send(
        self, payload: Mapping[str, Any], timeout: float
    ) -> Mapping[str, Any]:
        if not self._connected:
            raise RuntimeError("transport未连接")
        return self._server.handle(payload)

    def close(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected


@dataclass(frozen=True)
class ConstructionDemoApplication:
    skill: ConstructionDocumentSkill
    content_service: ContentService
    knowledge_service: ObservedKnowledgeService
    office_service: OfficeService
    artifact_service: ArtifactService
    audit_service: InMemoryAuditService
    office_runtime: OfficeCLIRuntimeProtocol


def create_construction_demo_application(
    office_runtime: OfficeCLIRuntimeProtocol | None = None,
) -> ConstructionDemoApplication:
    audit = InMemoryAuditService()
    clock = SystemClock()
    retry = RetryPolicy(1, 0.0, 0.0, 1.0, frozenset())
    read_policy = ServiceCallPolicy(
        OperationType.READ,
        Idempotency.IDEMPOTENT,
        retry,
        CircuitCallPolicy(),
        AuditPolicy(),
        30.0,
    )
    write_policy = ServiceCallPolicy(
        OperationType.WRITE,
        Idempotency.IDEMPOTENT_WITH_KEY,
        retry,
        CircuitCallPolicy(),
        AuditPolicy(),
        30.0,
    )

    construction_root = Path(__file__).parents[2] / "knowledge" / "construction"
    router = KnowledgeRouter(
        construction_root,
        construction_root / "standards",
    )
    knowledge_permissions = frozenset(
        {"KNOWLEDGE_READ", "STANDARDS_READ", "KNOWLEDGE_DOCUMENT_READ"}
    )
    knowledge_server = KnowledgeMCPServerAdapter(
        router,
        InMemoryMCPServerPermissionPolicy(
            {CONSTRUCTION_SKILL_ID: knowledge_permissions}
        ),
    )

    office_runtime = office_runtime or ConstructionOfficeRuntime()
    office_adapter = OfficeCLIAdapter(office_runtime, audit)
    office_permissions = frozenset(
        definition.permission
        for definition in OfficeMCPServerAdapter.TOOL_DEFINITIONS
    )
    office_server = OfficeMCPServerAdapter(
        office_adapter,
        InMemoryMCPServerPermissionPolicy(
            {CONSTRUCTION_SKILL_ID: office_permissions}
        ),
    )

    configs = {
        "knowledge-server": ServerConfig(
            "knowledge-server",
            "construction_knowledge",
            KnowledgeMCPServerAdapter.ALLOWED_TOOLS,
            1.0,
            30.0,
        ),
        "office-server": ServerConfig(
            "office-server",
            "construction_office",
            OfficeMCPServerAdapter.ALLOWED_TOOLS,
            1.0,
            30.0,
        ),
    }
    catalog = LegacyServerConfigCatalogAdapter(configs)
    client = MCPClient(
        catalog,
        catalog,
        ConnectionManager(
            {
                "construction_knowledge": lambda: LocalMCPTransport(
                    knowledge_server
                ),
                "construction_office": lambda: LocalMCPTransport(office_server),
            }
        ),
    )
    governance = ServiceCallExecutor(
        client,
        audit,
        RetryExecutor(clock),
        CircuitBreaker(CircuitBreakerPolicy(3, 10.0), clock),
        clock,
        GovernanceConfig(),
    )
    knowledge = KnowledgeService(
        governance,
        KnowledgeAccessPolicy(
            {
                CONSTRUCTION_SKILL_ID: frozenset(
                    {
                        KnowledgePermission.KNOWLEDGE_READ,
                        KnowledgePermission.STANDARDS_READ,
                        KnowledgePermission.KNOWLEDGE_DOCUMENT_READ,
                    }
                )
            }
        ),
        read_policy,
    )
    observed_knowledge = ObservedKnowledgeService(knowledge)
    content = ContentService(
        ConstructionContentPlanner(),
        observed_knowledge,
        ContentGenerator(ConstructionTextProvider()),
        audit,
        clock,
    )
    office = OfficeService(
        governance,
        {name: write_policy for name in OfficeService.TOOLS},
    )
    artifact = ArtifactService(NoopFileSystemService())
    skill = ConstructionDocumentSkill(
        content,
        observed_knowledge,
        PackageConstructionTemplateProvider(),
    )
    return ConstructionDemoApplication(
        skill,
        content,
        observed_knowledge,
        office,
        artifact,
        audit,
        office_runtime,
    )
