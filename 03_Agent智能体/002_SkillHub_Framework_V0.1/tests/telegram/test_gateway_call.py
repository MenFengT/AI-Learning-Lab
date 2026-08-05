import unittest

from app.adapters.telegram import (
    TelegramAdapter,
    TelegramGatewayAdapterProtocol,
    TelegramMessage,
    TelegramResponse,
)

from .helpers import AttachmentResolver, Gateway


class TelegramGatewayCallTests(unittest.TestCase):
    def test_adapter_calls_gateway_once_and_returns_standard_response(self) -> None:
        gateway = Gateway()
        adapter = TelegramAdapter(gateway, AttachmentResolver())

        response = adapter.handle(
            TelegramMessage("103", "10001", "20001", "生成方案")
        )

        self.assertIsInstance(adapter, TelegramGatewayAdapterProtocol)
        self.assertIsInstance(response, TelegramResponse)
        self.assertEqual(len(gateway.messages), 1)
        self.assertEqual(response.message, "处理完成")
        self.assertEqual(
            response.artifacts[0].artifact_id, "artifact-telegram-001"
        )


if __name__ == "__main__":
    unittest.main()
