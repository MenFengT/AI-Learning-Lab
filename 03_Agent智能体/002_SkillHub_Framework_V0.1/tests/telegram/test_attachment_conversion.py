import unittest

from app.adapters.telegram import (
    TelegramAdapter,
    TelegramAttachment,
    TelegramMessage,
)
from app.gateway import Attachment

from .helpers import AttachmentResolver, Gateway


class TelegramAttachmentConversionTests(unittest.TestCase):
    def test_attachment_is_resolved_without_content_processing(self) -> None:
        gateway = Gateway()
        resolver = AttachmentResolver()
        adapter = TelegramAdapter(gateway, resolver)
        source = TelegramAttachment(
            telegram_file_id="tg-file-001",
            filename="input.docx",
            mime_type="application/octet-stream",
            size=256,
        )

        adapter.handle(
            TelegramMessage("102", "10001", "20001", attachments=(source,))
        )

        self.assertEqual(resolver.attachments, [source])
        converted = gateway.messages[0].attachments[0]
        self.assertIsInstance(converted, Attachment)
        self.assertEqual(converted.file_name, source.filename)
        self.assertEqual(converted.media_type, source.mime_type)
        self.assertEqual(converted.size, source.size)
        self.assertEqual(converted.reference_id, "telegram-upload-001")
        self.assertEqual(converted.checksum, "0123456789abcdef")


if __name__ == "__main__":
    unittest.main()
