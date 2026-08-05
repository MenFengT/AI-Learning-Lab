import unittest

from app.content import (
    ContentGenerationContext,
    ContentGenerator,
    ContentGeneratorProtocol,
    ContentPlanner,
    ContentPlanningRequest,
    KnowledgeFragment,
    PackageContentTemplateLoader,
)


class RecordingProvider:
    def __init__(self) -> None:
        self.section_ids: list[str] = []

    def generate(self, section, context):
        self.section_ids.append(section.section_id)
        sources = ",".join(item.document_id for item in context.knowledge)
        return (f"{section.title}：{context.requirements}；来源={sources}",)


class ContentGeneratorContractTests(unittest.TestCase):
    def test_generator_returns_structured_draft_in_plan_order(self) -> None:
        plan = ContentPlanner(PackageContentTemplateLoader()).plan(
            ContentPlanningRequest(
                "report", "月度报告", "基于事实总结", ("summary", "progress")
            )
        )
        provider = RecordingProvider()
        generator = ContentGenerator(provider)
        draft = generator.generate(
            plan,
            ContentGenerationContext(
                title="月度报告",
                requirements="基于事实总结",
                knowledge=(
                    KnowledgeFragment(
                        "domain_facts",
                        "本月完成里程碑",
                        "domain",
                        "domain.monthly",
                        "1.0",
                    ),
                ),
            ),
        )

        self.assertIsInstance(generator, ContentGeneratorProtocol)
        self.assertEqual(provider.section_ids, ["summary", "progress"])
        self.assertEqual(draft.sections, ("summary", "progress"))
        self.assertEqual([item.order for item in draft.paragraphs], [1, 2])
        self.assertIn("domain.monthly", draft.paragraphs[0].text)


if __name__ == "__main__":
    unittest.main()
