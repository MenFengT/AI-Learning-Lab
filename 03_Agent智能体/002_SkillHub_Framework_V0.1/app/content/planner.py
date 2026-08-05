"""由外置模板生成内容结构计划。"""

from importlib.resources import files
import json
from typing import Any, Mapping

from .errors import ContentPlanningError, ContentTemplateError
from .models import (
    ContentPlan,
    ContentPlanningRequest,
    ContentSection,
    ContentTemplate,
)
from .protocols import ContentTemplateLoaderProtocol


class PackageContentTemplateLoader:
    """只读取包内固定JSON模板，拒绝任意资源路径。"""

    ALLOWED_TYPES = frozenset({"proposal", "report", "paper"})

    def load(self, document_type: str) -> ContentTemplate:
        if document_type not in self.ALLOWED_TYPES:
            raise ContentTemplateError(f"不支持的内容模板：{document_type}")
        try:
            raw = (
                files("app.content.templates")
                .joinpath(f"{document_type}.json")
                .read_text(encoding="utf-8")
            )
            payload = json.loads(raw)
            return _parse_template(payload)
        except ContentTemplateError:
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ContentTemplateError("内容模板格式无效") from exc


class ContentPlanner:
    """生成结构计划，不生成正文、不执行任务。"""

    def __init__(self, template_loader: ContentTemplateLoaderProtocol) -> None:
        self._template_loader = template_loader

    def plan(self, request: ContentPlanningRequest) -> ContentPlan:
        try:
            template = self._template_loader.load(request.document_type)
            sections = _select_sections(template, request.requested_sections)
            required = tuple(
                dict.fromkeys(
                    knowledge
                    for section in sections
                    for knowledge in section.required_knowledge
                )
            )
            return ContentPlan(
                document_type=request.document_type,
                sections=sections,
                section_order=tuple(item.section_id for item in sections),
                required_knowledge=required,
                metadata={
                    "title": request.title,
                    "template_schema_version": template.schema_version,
                },
            )
        except ContentTemplateError:
            raise
        except (TypeError, ValueError) as exc:
            raise ContentPlanningError("内容结构规划失败") from exc


def _parse_template(payload: Any) -> ContentTemplate:
    if not isinstance(payload, Mapping):
        raise ContentTemplateError("模板根节点必须是对象")
    raw_sections = payload.get("sections")
    if not isinstance(raw_sections, list):
        raise ContentTemplateError("模板sections必须是数组")
    sections = tuple(
        ContentSection(
            section_id=str(item["section_id"]),
            title=str(item["title"]),
            order=int(item["order"]),
            instructions=str(item["instructions"]),
            required_knowledge=tuple(item.get("required_knowledge", ())),
        )
        for item in raw_sections
        if isinstance(item, Mapping)
    )
    if len(sections) != len(raw_sections):
        raise ContentTemplateError("模板章节必须是对象")
    return ContentTemplate(
        document_type=str(payload["document_type"]),
        sections=sections,
        schema_version=str(payload.get("schema_version", "0.1")),
    )


def _select_sections(
    template: ContentTemplate, requested: tuple[str, ...]
) -> tuple[ContentSection, ...]:
    if not requested:
        return template.sections
    by_id = {item.section_id: item for item in template.sections}
    unknown = set(requested) - set(by_id)
    if unknown:
        raise ContentPlanningError(f"模板中不存在章节：{sorted(unknown)}")
    return tuple(
        ContentSection(
            section_id=by_id[section_id].section_id,
            title=by_id[section_id].title,
            order=index,
            instructions=by_id[section_id].instructions,
            required_knowledge=by_id[section_id].required_knowledge,
        )
        for index, section_id in enumerate(requested, 1)
    )
