import unittest

from app.content import (
    ContentPlanner,
    ContentPlannerProtocol,
    ContentPlanningRequest,
    PackageContentTemplateLoader,
)


class ContentPlannerContractTests(unittest.TestCase):
    def test_template_drives_structure_order_and_knowledge_requirements(self) -> None:
        planner = ContentPlanner(PackageContentTemplateLoader())
        plan = planner.plan(
            ContentPlanningRequest(
                document_type="proposal",
                title="建设方案",
                requirements="形成实施路径",
            )
        )

        self.assertIsInstance(planner, ContentPlannerProtocol)
        self.assertEqual(
            plan.section_order,
            ("background", "objectives", "implementation", "outcomes"),
        )
        self.assertEqual(
            plan.required_knowledge,
            (
                "domain_context",
                "domain_requirements",
                "domain_practices",
                "standards",
            ),
        )

    def test_requested_sections_are_validated_and_reordered(self) -> None:
        planner = ContentPlanner(PackageContentTemplateLoader())
        plan = planner.plan(
            ContentPlanningRequest(
                "report",
                "专题报告",
                "只输出问题与行动",
                ("issues", "actions"),
            )
        )
        self.assertEqual(plan.section_order, ("issues", "actions"))
        self.assertEqual([item.order for item in plan.sections], [1, 2])


if __name__ == "__main__":
    unittest.main()
