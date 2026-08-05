import unittest

from app.gateway import Attachment, AttachmentType, GatewayValidationError, UserMessage


def attachment(kind: AttachmentType = AttachmentType.WORD) -> Attachment:
    return Attachment(
        attachment_id="attachment-001",
        attachment_type=kind,
        file_name="input.docx",
        media_type="application/octet-stream",
        size=128,
        checksum="0123456789abcdef",
        reference_id="upload-001",
        metadata={"source": {"channel": "future"}},
    )


class MessageModelTests(unittest.TestCase):
    def test_text_and_attachment_message_is_normalized(self) -> None:
        message = UserMessage(
            message_id="message-001",
            user_id="user-001",
            text="  生成报告  ",
            attachments=(attachment(),),
            metadata={"locale": "zh-CN"},
        )
        self.assertEqual(message.text, "生成报告")
        self.assertEqual(message.attachments[0].reference_id, "upload-001")

    def test_file_only_message_is_supported_but_empty_message_is_rejected(self) -> None:
        message = UserMessage(
            "message-002", "user-001", attachments=(attachment(),)
        )
        self.assertIsNone(message.text)
        with self.assertRaises(GatewayValidationError):
            UserMessage("message-003", "user-001")


if __name__ == "__main__":
    unittest.main()
