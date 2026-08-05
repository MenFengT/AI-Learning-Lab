import unittest

from app.adapters.telegram import (
    TelegramAdapter,
    TelegramAttachment,
    TelegramAttachmentError,
    TelegramGatewayError,
    TelegramMessage,
)

from .helpers import AttachmentResolver, Gateway


class TelegramExceptionConversionTests(unittest.TestCase):
    def test_gateway_exception_is_wrapped_without_internal_details(self) -> None:
        adapter = TelegramAdapter(Gateway(fail=True), AttachmentResolver())
        with self.assertRaises(TelegramGatewayError) as captured:
            adapter.handle(TelegramMessage("104", "10001", "20001", "任务"))
        self.assertIsInstance(captured.exception.__cause__, RuntimeError)
        self.assertNotIn("unavailable", str(captured.exception))

    def test_attachment_resolver_exception_is_wrapped(self) -> None:
        adapter = TelegramAdapter(Gateway(), AttachmentResolver(fail=True))
        attachment = TelegramAttachment(
            "tg-file-001", "input.docx", "application/octet-stream", 1
        )
        with self.assertRaises(TelegramAttachmentError) as captured:
            adapter.handle(
                TelegramMessage(
                    "105", "10001", "20001", attachments=(attachment,)
                )
            )
        self.assertIsInstance(captured.exception.__cause__, RuntimeError)


if __name__ == "__main__":
    unittest.main()
