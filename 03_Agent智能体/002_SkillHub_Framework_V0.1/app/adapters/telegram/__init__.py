"""Telegram Adapter Layer公共契约。"""

from .adapter import TelegramAdapter
from .errors import (
    TelegramAdapterError,
    TelegramAttachmentError,
    TelegramGatewayError,
    TelegramMessageError,
)
from .models import TelegramAttachment, TelegramMessage, TelegramResponse
from .protocols import (
    TelegramAttachmentResolverProtocol,
    TelegramGatewayAdapterProtocol,
)

__all__ = [
    "TelegramAdapter",
    "TelegramAdapterError",
    "TelegramAttachment",
    "TelegramAttachmentError",
    "TelegramAttachmentResolverProtocol",
    "TelegramGatewayAdapterProtocol",
    "TelegramGatewayError",
    "TelegramMessage",
    "TelegramMessageError",
    "TelegramResponse",
]
