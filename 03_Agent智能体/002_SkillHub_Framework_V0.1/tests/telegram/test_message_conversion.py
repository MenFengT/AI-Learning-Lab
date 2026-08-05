import unittest

from app.adapters.telegram import TelegramAdapter, TelegramMessage
from app.gateway import AsyncTaskStatus, UserMessage

from .helpers import AttachmentResolver, Gateway


class TelegramMessageConversionTests(unittest.TestCase):
    def test_text_message_is_converted_to_gateway_message(self) -> None:
        gateway = Gateway()
        adapter = TelegramAdapter(gateway, AttachmentResolver())
        message = TelegramMessage(
            message_id="101",
            chat_id="-10001",
            user_id="20001",
            text="  生成月度报告  ",
            metadata={"language": "zh"},
        )

        response = adapter.handle(message)

        converted = gateway.messages[0]
        self.assertIsInstance(converted, UserMessage)
        self.assertEqual(converted.message_id, "telegram--10001-101")
        self.assertEqual(converted.user_id, "telegram-user-20001")
        self.assertEqual(converted.text, "生成月度报告")
        self.assertEqual(converted.metadata["channel"], "telegram")
        self.assertEqual(response.chat_id, "-10001")
        self.assertEqual(response.reply_to_message_id, "101")
        self.assertEqual(response.task_id, "task-telegram-001")
        self.assertEqual(response.status, AsyncTaskStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()
