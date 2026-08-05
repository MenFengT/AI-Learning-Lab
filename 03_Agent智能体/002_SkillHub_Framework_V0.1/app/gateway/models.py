"""Interaction Gateway不可变数据契约。"""

from dataclasses import dataclass, field
from enum import Enum
import re
from types import MappingProxyType, ModuleType
from typing import Any, Mapping

from .errors import GatewayValidationError


_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_CHECKSUM_PATTERN = re.compile(r"^[A-Fa-f0-9]{16,128}$")
_SENSITIVE_KEYS = frozenset(
    {"api_key", "apikey", "authorization", "password", "secret", "token"}
)


class AttachmentType(str, Enum):
    PDF = "PDF"
    CAD = "CAD"
    IMAGE = "IMAGE"
    WORD = "WORD"
    EXCEL = "EXCEL"
    PRESENTATION = "PRESENTATION"
    OTHER = "OTHER"


class AsyncTaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class Attachment:
    """已由入口保存后的附件引用；不包含文件内容或本地路径。"""

    attachment_id: str
    attachment_type: AttachmentType
    file_name: str
    media_type: str
    size: int
    checksum: str
    reference_id: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_id(self.attachment_id, "attachment_id")
        _validate_id(self.reference_id, "reference_id")
        if not isinstance(self.attachment_type, AttachmentType):
            raise GatewayValidationError("attachment_type无效")
        if not self.file_name.strip() or not self.media_type.strip():
            raise GatewayValidationError("file_name和media_type不能为空")
        if any(marker in self.file_name for marker in ("/", "\\", ":")):
            raise GatewayValidationError("file_name不能包含路径")
        if self.size < 0:
            raise GatewayValidationError("size不能小于0")
        if not _CHECKSUM_PATTERN.fullmatch(self.checksum):
            raise GatewayValidationError("checksum格式无效")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True)
class UserMessage:
    message_id: str
    user_id: str
    text: str | None = None
    attachments: tuple[Attachment, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_id(self.message_id, "message_id")
        _validate_id(self.user_id, "user_id")
        text = self.text.strip() if isinstance(self.text, str) else None
        attachments = tuple(self.attachments)
        if not text and not attachments:
            raise GatewayValidationError("消息必须包含文本或附件")
        if any(not isinstance(item, Attachment) for item in attachments):
            raise GatewayValidationError("attachments只能包含Attachment")
        ids = [item.attachment_id for item in attachments]
        if len(ids) != len(set(ids)):
            raise GatewayValidationError("attachment_id不能重复")
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "attachments", attachments)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True)
class AgentArtifactReference:
    artifact_id: str
    version: int
    artifact_type: str
    name: str

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id, "artifact_id")
        if self.version < 1:
            raise GatewayValidationError("artifact version必须从1开始")
        if not self.artifact_type.strip() or not self.name.strip():
            raise GatewayValidationError("artifact_type和name不能为空")


@dataclass(frozen=True)
class AgentInvocationResult:
    """Agent适配器返回的内部无通道任务快照。"""

    task_id: str
    status: AsyncTaskStatus
    message: str
    artifacts: tuple[AgentArtifactReference, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_response_fields(self)


@dataclass(frozen=True)
class AgentResponse:
    task_id: str
    status: AsyncTaskStatus
    message: str
    artifacts: tuple[AgentArtifactReference, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        _validate_response_fields(self)


def _validate_response_fields(value: AgentInvocationResult | AgentResponse) -> None:
    _validate_id(value.task_id, "task_id")
    if not isinstance(value.status, AsyncTaskStatus):
        raise GatewayValidationError("status无效")
    if not value.message.strip():
        raise GatewayValidationError("message不能为空")
    artifacts = tuple(value.artifacts)
    if any(not isinstance(item, AgentArtifactReference) for item in artifacts):
        raise GatewayValidationError("artifacts包含无效引用")
    object.__setattr__(value, "artifacts", artifacts)
    object.__setattr__(value, "metadata", _freeze_mapping(value.metadata))


def _validate_id(value: str, label: str) -> None:
    if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
        raise GatewayValidationError(f"{label}格式无效")


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GatewayValidationError("metadata必须为Mapping")
    frozen: dict[str, Any] = {}
    for key, child in value.items():
        normalized = str(key).casefold().replace("-", "_")
        if normalized in _SENSITIVE_KEYS:
            raise GatewayValidationError(f"metadata禁止敏感字段：{key}")
        frozen[str(key)] = _freeze_value(child)
    return MappingProxyType(frozen)


def _freeze_value(value: Any) -> Any:
    if callable(value) or isinstance(value, ModuleType):
        raise GatewayValidationError("metadata禁止可执行对象")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(child) for child in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(child) for child in value)
    raise GatewayValidationError("metadata只允许安全基础数据")
