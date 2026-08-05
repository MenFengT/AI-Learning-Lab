import unittest

from app.skills.document.errors import PromptLoadError
from app.skills.document.prompt_loader import PackagePromptLoader


class DocumentPromptLoadingTests(unittest.TestCase):
    def test_all_external_markdown_templates_load(self) -> None:
        loader = PackagePromptLoader()
        for name in ("proposal", "report", "paper"):
            with self.subTest(name=name):
                content = loader.load(name)
                self.assertIn("#", content)
                self.assertGreater(len(content), 20)

    def test_arbitrary_template_path_is_rejected(self) -> None:
        loader = PackagePromptLoader()
        with self.assertRaises(PromptLoadError):
            loader.load("../secret")


if __name__ == "__main__":
    unittest.main()
