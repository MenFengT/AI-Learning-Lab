"""施工行业文档生成Skill。"""

from importlib.resources import files
import json
from typing import Any, Mapping

from app.core.context import TaskContext
from app.services.content.models import ContentServiceRequest
from app.services.knowledge.models import KnowledgeQueryRequest, KnowledgeRuntimeContext
from app.skills.base_skill import BaseSkill

from .errors import ConstructionDependencyError, ConstructionRequestError, ConstructionTemplateError
from .models import (
    ConstructionDocumentRequest,
    ConstructionDocumentTemplate,
    ConstructionDocumentType,
    ConstructionTemplateSection,
    construction_request_from_mapping,
)
from .protocols import ConstructionTemplateProviderProtocol, ContentServiceProtocol, KnowledgeServiceProtocol


class PackageConstructionTemplateProvider:
    """只读取包内四个固定模板，不接受文件路径。"""

    _FILES = {
        ConstructionDocumentType.CONSTRUCTION_SCHEME: "construction_scheme.json",
        ConstructionDocumentType.TECHNICAL_DISCLOSURE: "technical_disclosure.json",
        ConstructionDocumentType.STARTUP_REPORT: "startup_report.json",
        ConstructionDocumentType.WEEKLY_REPORT: "weekly_report.json",
    }

    def load(self, document_type: ConstructionDocumentType) -> ConstructionDocumentTemplate:
        try:
            name = self._FILES[document_type]
            raw = files("app.skills.construction.templates").joinpath(name).read_text(encoding="utf-8")
            payload = json.loads(raw)
            return _parse_template(payload, document_type)
        except ConstructionTemplateError:
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ConstructionTemplateError("施工文档模板加载失败") from exc


class ConstructionDocumentSkill(BaseSkill):
    name = "construction_document"
    description = "生成施工技术方案、技术交底、开工报告和项目周报"
    keywords = ("施工方案", "技术交底", "开工报告", "项目周报")

    def __init__(
        self,
        content_service: ContentServiceProtocol,
        knowledge_service: KnowledgeServiceProtocol,
        template_provider: ConstructionTemplateProviderProtocol,
    ) -> None:
        self._content_service = content_service
        self._knowledge_service = knowledge_service
        self._template_provider = template_provider

    def execute(self, context: TaskContext) -> str:
        invocation = context.invocation_context
        if invocation is None:
            raise ConstructionRequestError("ConstructionDocumentSkill需要InvocationContext")
        request = context.metadata.get("construction_request")
        if request is None and isinstance(context.metadata.get("step_inputs"), Mapping):
            request = construction_request_from_mapping(context.metadata["step_inputs"])
        if not isinstance(request, ConstructionDocumentRequest):
            raise ConstructionRequestError("缺少ConstructionDocumentRequest")

        template = self._template_provider.load(request.document_type)
        knowledge = self._knowledge_service.query(
            KnowledgeQueryRequest(
                runtime_context=KnowledgeRuntimeContext(
                    task_id=invocation.task_id,
                    trace_id=invocation.trace_id,
                    span_id=invocation.span_id,
                    skill_id=invocation.skill_id,
                    user_id=invocation.user_id,
                    metadata=dict(invocation.metadata),
                ),
                query_text=request.knowledge_query,
                timeout=request.timeout,
            )
        )
        if not knowledge.success or knowledge.data is None:
            raise ConstructionDependencyError(knowledge.error_code or "KnowledgeService查询失败")
        hits = (*knowledge.data.domain_results, *knowledge.data.standards_results)
        content = self._content_service.generate_content(
            ContentServiceRequest(
                runtime_context=invocation,
                document_type="report",
                title=request.title,
                requirements=request.requirements,
                requested_sections=tuple(item.section_id for item in template.sections),
                knowledge_query=None,
                metadata={
                    **dict(request.metadata),
                    "construction_document_type": request.document_type.value,
                    "project_name": request.project_name,
                    "template_sections": tuple(item.title for item in template.sections),
                    "knowledge_fragments": tuple(hit.content for hit in hits if hit.content),
                    "knowledge_sources": tuple(hit.source.document_id for hit in hits),
                },
                timeout=request.timeout,
            )
        )
        if not content.success or content.data is None:
            raise ConstructionDependencyError(content.error_code or "ContentService生成失败")
        draft = content.data
        return "\n".join((draft.title, *(paragraph.text for paragraph in draft.paragraphs)))


def _parse_template(payload: Any, expected: ConstructionDocumentType) -> ConstructionDocumentTemplate:
    if not isinstance(payload, Mapping) or payload.get("document_type") != expected.value:
        raise ConstructionTemplateError("模板document_type不匹配")
    raw_sections = payload.get("sections")
    if not isinstance(raw_sections, list):
        raise ConstructionTemplateError("模板sections必须是数组")
    try:
        sections = tuple(
            ConstructionTemplateSection(
                section_id=str(item["section_id"]),
                title=str(item["title"]),
                order=int(item["order"]),
                guidance=str(item["guidance"]),
            )
            for item in raw_sections
            if isinstance(item, Mapping)
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ConstructionTemplateError("模板章节格式无效") from exc
    if len(sections) != len(raw_sections):
        raise ConstructionTemplateError("模板章节必须是对象")
    return ConstructionDocumentTemplate(expected, sections, str(payload.get("schema_version", "0.1")))
