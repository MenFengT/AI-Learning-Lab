"""Telegram消息到Interaction Gateway的纯转换适配器。"""

from typing import Any, Mapping

from app.gateway.models import Attachment, UserMessage
from app.gateway.protocols import InteractionGatewayProtocol

from .errors import TelegramAttachmentError, TelegramGatewayError
from .models import TelegramMessage, TelegramResponse
from .protocols import TelegramAttachmentResolverProtocol


class TelegramAdapter:
    """不连接Telegram API，不处理文件内容，不访问Agent内部。"""

    def __init__(
        self,
        gateway: InteractionGatewayProtocol,
        attachment_resolver: TelegramAttachmentResolverProtocol,
    ) -> None:
        self._gateway = gateway
        self._attachment_resolver = attachment_resolver

    def handle(self, message: TelegramMessage) -> TelegramResponse:
        if not isinstance(message, TelegramMessage):
            raise TypeError("message必须为TelegramMessage")
        attachments = tuple(
            self._resolve_attachment(item) for item in message.attachments
        )
        gateway_message = UserMessage(
            message_id=f"telegram-{message.chat_id}-{message.message_id}",
            user_id=f"telegram-user-{message.user_id}",
            text=message.text,
            attachments=attachments,
            metadata={
                **_plain(message.metadata),
                "channel": "telegram",
                "chat_id": message.chat_id,
                "telegram_message_id": message.message_id,
            },
        )
        try:
            response = self._gateway.handle(gateway_message)
        except Exception as exc:
            raise TelegramGatewayError("Interaction Gateway调用失败") from exc
        return TelegramResponse(
            chat_id=message.chat_id,
            reply_to_message_id=message.message_id,
            task_id=response.task_id,
            status=response.status,
            message=response.message,
            artifacts=response.artifacts,
            metadata=response.metadata,
        )

    def _resolve_attachment(self, attachment) -> Attachment:
        try:
            resolved = self._attachment_resolver.resolve(attachment)
        except Exception as exc:
            raise TelegramAttachmentError("Telegram附件登记解析失败") from exc
        if not isinstance(resolved, Attachment):
            raise TelegramAttachmentError(
                "附件解析端必须返回Gateway.Attachment"
            )
        if resolved.file_name != attachment.filename:
            raise TelegramAttachmentError("附件文件名在转换过程中发生变化")
        if resolved.media_type != attachment.mime_type:
            raise TelegramAttachmentError("附件MIME类型在转换过程中发生变化")
        if resolved.size != attachment.size:
            raise TelegramAttachmentError("附件size在转换过程中发生变化")
        return resolved


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(child) for key, child in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(_plain(child) for child in value)
    return value
