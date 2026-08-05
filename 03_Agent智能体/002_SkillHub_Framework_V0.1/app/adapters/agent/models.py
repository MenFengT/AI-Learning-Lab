"""Gateway 与 Agent Runtime 之间的不可变协议模型。"""

from dataclasses import dataclass, field
from types import MappingProxyType, ModuleType
from typing import Any, Mapping

from app.gateway.models import AgentArtifactReference, AsyncTaskStatus

from .errors import (
    AgentAdapterError,
    AgentRequestConversionError,
    AgentResultConversionError,
)


@dataclass(frozen=True)
class AgentAttachmentInput:
    """传给 Agent 的附件引用；不包含路径、句柄或文件内容。"""

    attachment_id: str
    reference_id: str
    attachment_type: str
    file_name: str
    media_type: str
    size: int
    checksum: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.attachment_id or not self.reference_id:
            raise AgentRequestConversionError("附件标识不能为空")
        if not self.file_name or not self.media_type or self.size < 0:
            raise AgentRequestConversionError("附件引用无效")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True)
class AgentTaskInput:
    """Agent Runtime 的标准任务输入。"""

    message_id: str
    user_id: str
    user_task: str
    attachments: tuple[AgentAttachmentInput, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.message_id or not self.user_id:
            raise AgentRequestConversionError("消息和用户标识不能为空")
        if not self.user_task.strip() and not self.attachments:
            raise AgentRequestConversionError("Agent任务必须包含文本或附件")
        if any(not isinstance(item, AgentAttachmentInput) for item in self.attachments):
            raise AgentRequestConversionError("attachments 包含无效引用")
        object.__setattr__(self, "user_task", self.user_task.strip())
        object.__setattr__(self, "attachments", tuple(self.attachments))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True)
class AgentTaskResult:
    """Agent Runtime 的通道无关执行结果。"""

    task_id: str
    status: AsyncTaskStatus
    message: str
    artifacts: tuple[AgentArtifactReference, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.task_id or not isinstance(self.status, AsyncTaskStatus):
            raise AgentResultConversionError("Agent结果标识或状态无效")
        if not self.message.strip():
            raise AgentResultConversionError("Agent结果消息不能为空")
        if any(not isinstance(item, AgentArtifactReference) for item in self.artifacts):
            raise AgentResultConversionError("Agent结果包含无效产物引用")
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AgentAdapterError("metadata 必须是 Mapping")
    return MappingProxyType({str(key): _freeze_value(child) for key, child in value.items()})


def _freeze_value(value: Any) -> Any:
    if callable(value) or isinstance(value, ModuleType):
        raise AgentAdapterError("metadata 禁止可执行对象")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(child) for child in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(child) for child in value)
    raise AgentAdapterError("metadata 仅允许安全基础数据")
