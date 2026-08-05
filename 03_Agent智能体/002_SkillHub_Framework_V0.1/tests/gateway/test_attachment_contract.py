import unittest

from app.gateway import AttachmentType, GatewayValidationError

from .test_message_models import attachment


class AttachmentContractTests(unittest.TestCase):
    def test_future_attachment_types_are_reserved(self) -> None:
        expected = {
            AttachmentType.PDF,
            AttachmentType.CAD,
            AttachmentType.IMAGE,
            AttachmentType.WORD,
            AttachmentType.EXCEL,
            AttachmentType.PRESENTATION,
        }
        self.assertTrue(expected.issubset(set(AttachmentType)))
        for kind in expected:
            with self.subTest(kind=kind):
                self.assertEqual(attachment(kind).attachment_type, kind)

    def test_attachment_rejects_paths_and_contains_no_content_field(self) -> None:
        self.assertNotIn("content", attachment().__dataclass_fields__)
        self.assertNotIn("path", attachment().__dataclass_fields__)
        with self.assertRaises(GatewayValidationError):
            type(attachment())(
                "attachment-002",
                AttachmentType.PDF,
                "C:/secret.pdf",
                "application/pdf",
                10,
                "0123456789abcdef",
                "upload-002",
            )


if __name__ == "__main__":
    unittest.main()
