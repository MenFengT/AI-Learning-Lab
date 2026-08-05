"""Telegram Adapter Layer错误。"""


class TelegramAdapterError(RuntimeError):
    """Telegram适配层基础错误。"""


class TelegramMessageError(TelegramAdapterError, ValueError):
    """Telegram消息或附件不符合适配契约。"""


class TelegramAttachmentError(TelegramAdapterError):
    """附件尚未转换为可信Gateway引用。"""


class TelegramGatewayError(TelegramAdapterError):
    """Interaction Gateway调用失败。"""
