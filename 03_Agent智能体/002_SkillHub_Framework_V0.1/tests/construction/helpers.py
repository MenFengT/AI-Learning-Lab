from app.content.models import ContentDraft, ContentParagraph
from app.core.context import TaskContext
from app.runtime.invocation_context import InvocationContext
from app.services.knowledge.models import KnowledgeHit, KnowledgeQueryData, SourceReference
from app.services.models import ServiceResult
from app.skills.construction import (
    ConstructionDocumentRequest,
    ConstructionDocumentType,
    ConstructionDocumentSkill,
    PackageConstructionTemplateProvider,
)


class RecordingContentService:
    def __init__(self) -> None:
        self.requests = []

    def generate_content(self, request):
        self.requests.append(request)
        return ServiceResult(
            True,
            ContentDraft(
                request.title,
                request.requested_sections,
                tuple(
                    ContentParagraph(section, index, f"{section}生成内容")
                    for index, section in enumerate(request.requested_sections, 1)
                ),
            ),
            None,
            "ok",
            request.runtime_context.trace_id,
        )


class RecordingKnowledgeService:
    def __init__(self) -> None:
        self.requests = []

    def query(self, request):
        self.requests.append(request)
        source = SourceReference("domain-construction-001", "1.0", "2026-08-05T00:00:00Z", "domain", "fragment-001", "DOMAIN")
        hit = KnowledgeHit("施工知识", "施工组织与质量安全要求", source, "ACTIVE")
        return ServiceResult(
            True,
            KnowledgeQueryData((hit,), (), ()),
            None,
            "ok",
            request.runtime_context.trace_id,
        )


def invocation() -> InvocationContext:
    return InvocationContext(
        "task-construction-001", "trace-construction-001",
        "span-construction-001", "local/construction_document@0.1.0",
        "user-001", {"channel": "test"},
    )


def request(document_type=ConstructionDocumentType.CONSTRUCTION_SCHEME):
    return ConstructionDocumentRequest(
        document_type,
        "地下室施工技术方案",
        "生成符合项目实际情况的施工技术文件",
        "地下室施工工艺、质量控制及安全规范",
        "示例工程",
    )


def build_skill():
    content = RecordingContentService()
    knowledge = RecordingKnowledgeService()
    skill = ConstructionDocumentSkill(
        content, knowledge, PackageConstructionTemplateProvider()
    )
    return skill, content, knowledge


def context(document_type=ConstructionDocumentType.CONSTRUCTION_SCHEME):
    return TaskContext(
        "生成施工文档",
        metadata={"construction_request": request(document_type)},
        invocation_context=invocation(),
    )
