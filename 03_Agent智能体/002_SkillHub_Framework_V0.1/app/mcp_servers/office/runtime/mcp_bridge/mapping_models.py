"""SkillHub Office能力到外部OfficeCLI MCP调用的强类型模型。"""

from dataclasses import dataclass
from enum import Enum
import re
from types import MappingProxyType
from typing import Mapping

from .errors import BridgeRequestError


class OfficeCapability(str, Enum):
    CREATE_DOCUMENT = "office.create_document"
    UPDATE_DOCUMENT = "office.update_document"
    CONVERT_DOCUMENT = "office.convert_document"
    EXPORT_DOCUMENT = "office.export_document"


@dataclass(frozen=True)
class OfficeDocumentContent:
    """允许Mapper接收的最小文档内容，不包含命令或路径。"""

    title: str
    paragraphs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.title, str) or not self.title.strip():
            raise BridgeRequestError("文档标题不能为空")
        paragraphs = tuple(self.paragraphs)
        if any(not isinstance(item, str) or not item.strip() for item in paragraphs):
            raise BridgeRequestError("文档段落必须是非空字符串")
        object.__setattr__(self, "title", self.title.strip())
        object.__setattr__(self, "paragraphs", paragraphs)


@dataclass(frozen=True)
class OfficeCapabilityRequest:
    """Mapper唯一输入；文件位置由task_id和文件名推导。"""

    capability: OfficeCapability
    task_id: str
    document_name: str
    content: OfficeDocumentContent

    def __post_init__(self) -> None:
        if not isinstance(self.capability, OfficeCapability):
            raise BridgeRequestError("Office能力不在固定白名单")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", self.task_id):
            raise BridgeRequestError("task_id格式无效")
        _validate_document_name(self.document_name)
        if not isinstance(self.content, OfficeDocumentContent):
            raise BridgeRequestError("content必须是OfficeDocumentContent")


@dataclass(frozen=True)
class ExternalOfficeCLICall:
    """符合OfficeCLI 1.0.143真实MCP Schema的不可变调用。"""

    tool_name: str
    arguments: Mapping[str, tuple[str, ...]]

    def __post_init__(self) -> None:
        if self.tool_name != "officecli":
            raise BridgeRequestError("外部Tool必须固定为officecli")
        if set(self.arguments) != {"command"}:
            raise BridgeRequestError("外部参数只能包含command")
        command = self.arguments.get("command")
        if not isinstance(command, tuple) or not command:
            raise BridgeRequestError("command必须是非空argv元组")
        if any(not isinstance(item, str) or not item for item in command):
            raise BridgeRequestError("command元素必须是非空字符串")
        object.__setattr__(
            self,
            "arguments",
            MappingProxyType({"command": tuple(command)}),
        )


@dataclass(frozen=True)
class OfficeCapabilityPlan:
    capability: OfficeCapability
    calls: tuple[ExternalOfficeCLICall, ...]

    def __post_init__(self) -> None:
        calls = tuple(self.calls)
        if not calls:
            raise BridgeRequestError("映射计划至少包含一个调用")
        object.__setattr__(self, "calls", calls)


def _validate_document_name(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise BridgeRequestError("document_name不能为空")
    if value != value.strip() or value in {".", ".."}:
        raise BridgeRequestError("document_name格式无效")
    if any(marker in value for marker in ("/", "\\", ":", "..")):
        raise BridgeRequestError("document_name禁止路径或路径穿越")
    if any(ord(character) < 32 for character in value):
        raise BridgeRequestError("document_name禁止控制字符")
    if value.casefold().endswith((".docx", ".xlsx", ".pptx")) is False:
        raise BridgeRequestError("document_name必须是受支持的Office文件")
