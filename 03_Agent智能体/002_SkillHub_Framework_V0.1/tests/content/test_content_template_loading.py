import unittest

from app.content.errors import ContentTemplateError
from app.content.planner import PackageContentTemplateLoader


class ContentTemplateLoadingTests(unittest.TestCase):
    def test_external_templates_load_with_strong_contract(self) -> None:
        loader = PackageContentTemplateLoader()
        for document_type in ("proposal", "report", "paper"):
            with self.subTest(document_type=document_type):
                template = loader.load(document_type)
                self.assertEqual(template.document_type, document_type)
                self.assertGreater(len(template.sections), 0)
                self.assertTrue(
                    all(section.instructions for section in template.sections)
                )

    def test_arbitrary_resource_path_is_rejected(self) -> None:
        with self.assertRaises(ContentTemplateError):
            PackageContentTemplateLoader().load("../secret")


if __name__ == "__main__":
    unittest.main()
