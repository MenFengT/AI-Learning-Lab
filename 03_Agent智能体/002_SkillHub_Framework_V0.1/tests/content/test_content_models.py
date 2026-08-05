import unittest
from dataclasses import FrozenInstanceError

from app.content import (
    ContentDraft,
    ContentParagraph,
    ContentPlan,
    ContentSection,
)


class ContentModelTests(unittest.TestCase):
    def test_plan_contract_and_deep_metadata_isolation(self) -> None:
        source = {"request": {"tags": ["a"]}}
        section = ContentSection(
            "background",  "背景", 1, "说明背景", ("domain_context",)
        )
        plan = ContentPlan(
            document_type="proposal",
            sections=(section,),
            section_order=("background",),
            required_knowledge=("domain_context",),
            metadata=source,
        )
        source["request"]["tags"].append("b")

        self.assertEqual(plan.metadata["request"]["tags"], ("a",))
        with self.assertRaises(FrozenInstanceError):
            plan.document_type = "report"  # type: ignore[misc]

    def test_draft_requires_ordered_paragraphs_in_declared_sections(self) -> None:
        draft = ContentDraft(
            title="测试",
            sections=("summary",),
            paragraphs=(ContentParagraph("summary", 1, "正文"),),
        )
        self.assertEqual(draft.paragraphs[0].text, "正文")
        with self.assertRaises(ValueError):
            ContentDraft(
                title="测试",
                sections=("summary",),
                paragraphs=(ContentParagraph("other", 1, "正文"),),
            )


if __name__ == "__main__":
    unittest.main()
