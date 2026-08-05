"""Content Layer不可变数据契约。"""

from copy import deepcopy
from collections.abc import Iterator
from dataclasses import dataclass, field
import re
from types import ModuleType
from typing import Any, Mapping


_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_DOCUMENT_TYPES = frozenset({"proposal", "report", "paper"})


class _ImmutableMapping(Mapping[str, Any]):
    def __init__(self, value: Mapping[str, Any]) -> None:
        self._value = {
            str(key): _freeze_value(child)
            for key, child in deepcopy(dict(value)).items()
        }

    def __getitem__(self, key: str) -> Any:
        return self._value[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._value)

    def __len__(self) -> int:
        return len(self._value)

    def __deepcopy__(self, memo: dict[int, Any]) -> "_ImmutableMapping":
        return _ImmutableMapping(deepcopy(self._value, memo))


@dataclass(frozen=True)
class ContentSection:
    section_id: str
    title: str
    order: int
    instructions: str
    required_knowledge: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _IDENTIFIER.fullmatch(self.section_id):
            raise ValueError("section_id格式无效")
        if not self.title.strip() or not self.instructions.strip():
            raise ValueError("章节title和instructions不能为空")
        if self.order < 1:
            raise ValueError("章节order必须从1开始")
        knowledge = tuple(item.strip() for item in self.required_knowledge)
        if any(not item for item in knowledge):
            raise ValueError("required_knowledge不能包含空值")
        object.__setattr__(self, "required_knowledge", knowledge)


@dataclass(frozen=True)
class ContentTemplate:
    document_type: str
    sections: tuple[ContentSection, ...]
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        _validate_document_type(self.document_type)
        sections = tuple(self.sections)
        if not sections:
            raise ValueError("ContentPlan至少包含一个章节")
        if not sections:
            raise ValueError("模板至少包含一个章节")
        if [item.order for item in sections] != list(range(1, len(sections) + 1)):
            raise ValueError("模板章节order必须连续")
        ids = [item.section_id for item in sections]
        if len(ids) != len(set(ids)):
            raise ValueError("模板section_id不能重复")
        object.__setattr__(self, "sections", sections)


@dataclass(frozen=True)
class ContentPlanningRequest:
    document_type: str
    title: str
    requirements: str
    requested_sections: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_document_type(self.document_type)
        if not self.title.strip() or not self.requirements.strip():
            raise ValueError("title和requirements不能为空")
        requested = tuple(item.strip() for item in self.requested_sections)
        if any(not item for item in requested):
            raise ValueError("requested_sections不能包含空值")
        object.__setattr__(self, "requested_sections", requested)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True)
class ContentPlan:
    document_type: str
    sections: tuple[ContentSection, ...]
    section_order: tuple[str, ...]
    required_knowledge: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        _validate_document_type(self.document_type)
        sections = tuple(self.sections)
        order = tuple(self.section_order)
        expected_order = tuple(item.section_id for item in sections)
        if order != expected_order:
            raise ValueError("section_order必须与sections顺序一致")
        required = tuple(dict.fromkeys(self.required_knowledge))
        if any(not item.strip() for item in required):
            raise ValueError("required_knowledge不能包含空值")
        object.__setattr__(self, "sections", sections)
        object.__setattr__(self, "section_order", order)
        object.__setattr__(self, "required_knowledge", required)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True)
class KnowledgeFragment:
    knowledge_key: str
    content: str
    source: str
    document_id: str
    version: str

    def __post_init__(self) -> None:
        for label in (
            "knowledge_key",
            "content",
            "source",
            "document_id",
            "version",
        ):
            if not getattr(self, label).strip():
                raise ValueError(f"{label}不能为空")


@dataclass(frozen=True)
class ContentGenerationContext:
    title: str
    requirements: str
    knowledge: tuple[KnowledgeFragment, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.title.strip() or not self.requirements.strip():
            raise ValueError("title和requirements不能为空")
        object.__setattr__(self, "knowledge", tuple(self.knowledge))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True)
class ContentParagraph:
    section_id: str
    order: int
    text: str

    def __post_init__(self) -> None:
        if not _IDENTIFIER.fullmatch(self.section_id):
            raise ValueError("paragraph.section_id格式无效")
        if self.order < 1 or not self.text.strip():
            raise ValueError("paragraph order和text无效")


@dataclass(frozen=True)
class ContentDraft:
    title: str
    sections: tuple[str, ...]
    paragraphs: tuple[ContentParagraph, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("title不能为空")
        sections = tuple(self.sections)
        paragraphs = tuple(self.paragraphs)
        if not sections or not paragraphs:
            raise ValueError("草稿必须包含章节和段落")
        if any(item.section_id not in sections for item in paragraphs):
            raise ValueError("段落必须属于已声明章节")
        if [item.order for item in paragraphs] != list(
            range(1, len(paragraphs) + 1)
        ):
            raise ValueError("段落order必须连续")
        object.__setattr__(self, "sections", sections)
        object.__setattr__(self, "paragraphs", paragraphs)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


def _validate_document_type(value: str) -> None:
    if value not in _DOCUMENT_TYPES:
        raise ValueError(f"不支持的document_type：{value}")


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("metadata必须为Mapping")
    return _ImmutableMapping(value)


def _freeze_value(value: Any) -> Any:
    if callable(value) or isinstance(value, ModuleType):
        raise ValueError("metadata禁止保存可执行对象")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(child) for child in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(child) for child in value)
    raise ValueError("metadata只允许安全基础数据")
