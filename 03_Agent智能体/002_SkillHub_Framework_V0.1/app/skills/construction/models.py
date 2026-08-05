"""Construction Document Skill 业务数据契约。"""

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType, ModuleType
from typing import Any, Mapping

from .errors import ConstructionRequestError, ConstructionTemplateError


class ConstructionDocumentType(str, Enum):
    CONSTRUCTION_SCHEME = "construction_scheme"
    TECHNICAL_DISCLOSURE = "technical_disclosure"
    STARTUP_REPORT = "startup_report"
    WEEKLY_REPORT = "weekly_report"


@dataclass(frozen=True)
class ConstructionDocumentRequest:
    document_type: ConstructionDocumentType
    title: str
    requirements: str
    knowledge_query: str
    project_name: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    timeout: float = 10.0

    def __post_init__(self) -> None:
        if not isinstance(self.document_type, ConstructionDocumentType):
            raise ConstructionRequestError("document_type无效")
        for label in ("title", "requirements", "knowledge_query"):
            value = getattr(self, label)
            if not isinstance(value, str) or not value.strip():
                raise ConstructionRequestError(f"{label}不能为空")
            object.__setattr__(self, label, value.strip())
        if self.project_name is not None and not self.project_name.strip():
            raise ConstructionRequestError("project_name不能为空字符串")
        if self.timeout <= 0:
            raise ConstructionRequestError("timeout必须大于0")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True)
class ConstructionTemplateSection:
    section_id: str
    title: str
    order: int
    guidance: str

    def __post_init__(self) -> None:
        if not self.section_id.strip() or not self.title.strip() or not self.guidance.strip():
            raise ConstructionTemplateError("模板章节字段不能为空")
        if self.order < 1:
            raise ConstructionTemplateError("模板章节order必须从1开始")


@dataclass(frozen=True)
class ConstructionDocumentTemplate:
    document_type: ConstructionDocumentType
    sections: tuple[ConstructionTemplateSection, ...]
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        if not isinstance(self.document_type, ConstructionDocumentType):
            raise ConstructionTemplateError("模板document_type无效")
        sections = tuple(self.sections)
        if not sections:
            raise ConstructionTemplateError("模板至少包含一个章节")
        if tuple(item.order for item in sections) != tuple(range(1, len(sections) + 1)):
            raise ConstructionTemplateError("模板章节order必须连续")
        if len({item.section_id for item in sections}) != len(sections):
            raise ConstructionTemplateError("模板section_id不能重复")
        object.__setattr__(self, "sections", sections)


def construction_request_from_mapping(value: Mapping[str, Any]) -> ConstructionDocumentRequest:
    try:
        metadata = value.get("metadata", {})
        return ConstructionDocumentRequest(
            document_type=ConstructionDocumentType(str(value["document_type"])),
            title=str(value["title"]),
            requirements=str(value["requirements"]),
            knowledge_query=str(value["knowledge_query"]),
            project_name=(str(value["project_name"]) if value.get("project_name") is not None else None),
            metadata=metadata if isinstance(metadata, Mapping) else {},
            timeout=float(value.get("timeout", 10.0)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ConstructionRequestError("施工文档输入映射无效") from exc


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConstructionRequestError("metadata必须是Mapping")
    copied = deepcopy(dict(value))
    return MappingProxyType({str(key): _freeze_value(child) for key, child in copied.items()})


def _freeze_value(value: Any) -> Any:
    if callable(value) or isinstance(value, ModuleType):
        raise ConstructionRequestError("metadata禁止可执行对象")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(child) for child in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(child) for child in value)
    raise ConstructionRequestError("metadata仅允许安全基础数据")
