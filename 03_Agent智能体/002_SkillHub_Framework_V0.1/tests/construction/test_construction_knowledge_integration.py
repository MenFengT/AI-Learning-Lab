from pathlib import Path

from app.content.models import ContentDraft, ContentParagraph
from app.core.context import TaskContext
from app.knowledge.knowledge_router import KnowledgeRouter
from app.knowledge.models import KnowledgeCategory
from app.runtime.invocation_context import InvocationContext
from app.services.knowledge.models import (
    KnowledgeHit,
    KnowledgeQueryData,
    SourceReference,
)
from app.services.models import ServiceResult
from app.skills.construction import (
    ConstructionDocumentRequest,
    ConstructionDocumentSkill,
    ConstructionDocumentType,
    PackageConstructionTemplateProvider,
)


CONSTRUCTION_ROOT = (
    Path(__file__).parents[2] / "app" / "knowledge" / "construction"
)


class RouterBackedKnowledgeService:
    """测试适配器：通过真实 MD + INDEX Router 提供 KnowledgeService 契约。"""

    def __init__(self, router: KnowledgeRouter) -> None:
        self._router = router
        self.requests = []

    def query(self, request):
        self.requests.append(request)
        result = self._router.query(request.query_text)
        return ServiceResult(
            success=True,
            data=KnowledgeQueryData(
                domain_results=tuple(
                    self._to_hit(document) for document in result.domain_results
                ),
                standards_results=tuple(
                    self._to_hit(document)
                    for document in result.standards_results
                ),
                conflicts=(),
            ),
            error_code=None,
            message="ok",
            trace_id=request.runtime_context.trace_id,
        )

    @staticmethod
    def _to_hit(document):
        source = document.source
        return KnowledgeHit(
            title=document.title,
            content=document.content,
            source=SourceReference(
                document_id=source.document_id,
                version=source.version,
                timestamp=source.timestamp,
                source=source.source,
                fragment_id=source.fragment_id,
                category=source.category.value,
            ),
            status=document.status,
        )


class RecordingContentService:
    def __init__(self) -> None:
        self.requests = []

    def generate_content(self, request):
        self.requests.append(request)
        return ServiceResult(
            success=True,
            data=ContentDraft(
                title=request.title,
                sections=request.requested_sections,
                paragraphs=tuple(
                    ContentParagraph(section_id, order, f"{section_id}内容")
                    for order, section_id in enumerate(
                        request.requested_sections, 1
                    )
                ),
            ),
            error_code=None,
            message="ok",
            trace_id=request.runtime_context.trace_id,
        )


def _router() -> KnowledgeRouter:
    return KnowledgeRouter(
        CONSTRUCTION_ROOT,
        CONSTRUCTION_ROOT / "standards",
    )


def test_construction_index_separates_domain_and_standards() -> None:
    result = _router().query("生成地下室防水施工方案")

    assert result.domain_results
    assert result.standards_results
    assert all(
        item.source.category is KnowledgeCategory.DOMAIN
        for item in result.domain_results
    )
    assert all(
        item.source.category is KnowledgeCategory.STANDARD
        for item in result.standards_results
    )
    assert result.domain_results[0].source.document_id == (
        "construction.basement_waterproofing.practice"
    )
    assert result.standards_results[0].source.document_id == (
        "construction.safety_civilized.requirements"
    )


def test_construction_skill_passes_real_knowledge_fragments_to_content() -> None:
    knowledge = RouterBackedKnowledgeService(_router())
    content = RecordingContentService()
    skill = ConstructionDocumentSkill(
        content,
        knowledge,
        PackageConstructionTemplateProvider(),
    )
    invocation = InvocationContext(
        task_id="task-basement-waterproofing",
        trace_id="trace-basement-waterproofing",
        span_id="span-basement-waterproofing",
        skill_id="local/construction_document@0.1.0",
        user_id="user-001",
        metadata={"channel": "test"},
    )
    request = ConstructionDocumentRequest(
        document_type=ConstructionDocumentType.CONSTRUCTION_SCHEME,
        title="地下室防水施工方案",
        requirements="生成地下室防水施工方案",
        knowledge_query="生成地下室防水施工方案",
        project_name="示例工程",
    )

    result = skill.execute(
        TaskContext(
            user_task="生成地下室防水施工方案",
            metadata={"construction_request": request},
            invocation_context=invocation,
        )
    )

    assert result.startswith("地下室防水施工方案")
    assert len(knowledge.requests) == 1
    assert len(content.requests) == 1
    content_request = content.requests[0]
    assert content_request.runtime_context == invocation
    assert content_request.metadata["knowledge_fragments"]
    assert any(
        "地下室防水施工方案" in fragment
        for fragment in content_request.metadata["knowledge_fragments"]
    )
    assert "construction.basement_waterproofing.practice" in (
        content_request.metadata["knowledge_sources"]
    )
    assert "construction.safety_civilized.requirements" in (
        content_request.metadata["knowledge_sources"]
    )
