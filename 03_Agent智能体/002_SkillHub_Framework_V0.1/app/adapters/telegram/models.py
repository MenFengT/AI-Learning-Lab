"""Telegram Adapter不可变输入输出契约。"""

from dataclasses import dataclass, field
from typing import Any, Mapping
import re
from types import MappingProxyType, ModuleType

from app.gateway.models import AgentArtifactReference, AsyncTaskStatus

from .errors import TelegramMessageError


_POSITIVE_ID = re.compile(r"^[1-9][0-9]*$")
_CHAT_ID = re.compile(r"^-?[1-9][0-9]*$")


@dataclass(frozen=True)
class TelegramAttachment:
    telegram_file_id: str
    filename: str
    mime_type: str
    size: int

    def __post_init__(self) -> None:
        if not self.telegram_file_id.strip():
            raise TelegramMessageError("telegram_file_id不能为空")
        if not self.filename.strip() or not self.mime_type.strip():
            raise TelegramMessageError("filename和mime_type不能为空")
        if any(marker in self.filename for marker in ("/", "\\", ":")):
            raise TelegramMessageError("filename不能包含路径")
        if self.size < 0:
            raise TelegramMessageError("size不能小于0")


@dataclass(frozen=True)
class TelegramMessage:
    message_id: str
    chat_id: str
    user_id: str
    text: str | None = None
    attachments: tuple[TelegramAttachment, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _POSITIVE_ID.fullmatch(self.message_id):
            raise TelegramMessageError("message_id必须为正整数标识")
        if not _CHAT_ID.fullmatch(self.chat_id):
            raise TelegramMessageError("chat_id格式无效")
        if not _POSITIVE_ID.fullmatch(self.user_id):
            raise TelegramMessageError("user_id必须为正整数标识")
        text = self.text.strip() if isinstance(self.text, str) else None
        attachments = tuple(self.attachments)
        if not text and not attachments:
            raise TelegramMessageError("Telegram消息必须包含文本或附件")
        if any(not isinstance(item, TelegramAttachment) for item in attachments):
            raise TelegramMessageError("attachments包含无效对象")
        file_ids = [item.telegram_file_id for item in attachments]
        if len(file_ids) != len(set(file_ids)):
            raise TelegramMessageError("telegram_file_id不能重复")
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "attachments", attachments)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True)
class TelegramResponse:
    chat_id: str
    reply_to_message_id: str
    task_id: str
    status: AsyncTaskStatus
    message: str
    artifacts: tuple[AgentArtifactReference, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _CHAT_ID.fullmatch(self.chat_id):
            raise TelegramMessageError("response.chat_id格式无效")
        if not _POSITIVE_ID.fullmatch(self.reply_to_message_id):
            raise TelegramMessageError("reply_to_message_id格式无效")
        if not self.task_id.strip() or not self.message.strip():
            raise TelegramMessageError("task_id和message不能为空")
        if not isinstance(self.status, AsyncTaskStatus):
            raise TelegramMessageError("status无效")
        artifacts = tuple(self.artifacts)
        if any(not isinstance(item, AgentArtifactReference) for item in artifacts):
            raise TelegramMessageError("artifacts包含无效引用")
        object.__setattr__(self, "artifacts", artifacts)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TelegramMessageError("metadata必须为Mapping")
    return MappingProxyType(
        {str(key): _freeze_value(child) for key, child in value.items()}
    )


def _freeze_value(value: Any) -> Any:
    if callable(value) or isinstance(value, ModuleType):
        raise TelegramMessageError("metadata禁止可执行对象")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(child) for child in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(child) for child in value)
    raise TelegramMessageError("metadata只允许安全基础数据")
