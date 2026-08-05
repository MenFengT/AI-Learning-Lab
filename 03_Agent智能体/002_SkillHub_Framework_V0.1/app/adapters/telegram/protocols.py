"""Telegram Gateway与附件登记解析端口。"""

from typing import Protocol, runtime_checkable

from app.gateway.models import Attachment

from .models import TelegramAttachment, TelegramMessage, TelegramResponse


@runtime_checkable
class TelegramAttachmentResolverProtocol(Protocol):
    """由外部传输层提供可信checksum和上传引用，不在Adapter内下载。"""

    def resolve(self, attachment: TelegramAttachment) -> Attachment: ...


@runtime_checkable
class TelegramGatewayAdapterProtocol(Protocol):
    def handle(self, message: TelegramMessage) -> TelegramResponse: ...
