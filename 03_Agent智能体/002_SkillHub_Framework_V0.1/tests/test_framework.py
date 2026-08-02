import ast
import unittest
from pathlib import Path

from app.config.settings import Settings
from app.core.agent import SkillHubAgent
from app.core.context import TaskContext
from app.core.skill_router import SkillRouter
from app.knowledge.knowledge_router import KnowledgeRouter
from app.main import build_agent
from app.skills.base_skill import BaseSkill


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TrackingSkill(BaseSkill):
    name = "tracking"
    description = "测试 Skill"
    keywords = ("跟踪",)

    def __init__(self) -> None:
        self.executed = False

    def execute(self, context: TaskContext) -> str:
        self.executed = True
        return context.user_task


class SkillHubFrameworkTests(unittest.TestCase):
    def test_minimum_demo_chain(self) -> None:
        result = build_agent().run("请演示任务，返回结果")
        self.assertEqual(result, "DemoSkill 已处理任务：请演示任务；返回结果")

    def test_router_selects_but_does_not_execute(self) -> None:
        router = SkillRouter()
        skill = TrackingSkill()
        router.register(skill)

        selected = router.select("请跟踪这个任务")

        self.assertIs(selected, skill)
        self.assertFalse(skill.executed)

    def test_agent_schedules_selected_skill(self) -> None:
        router = SkillRouter()
        skill = TrackingSkill()
        router.register(skill)

        result = SkillHubAgent(router).run("跟踪任务")

        self.assertEqual(result, "跟踪任务")
        self.assertTrue(skill.executed)

    def test_registry_rejects_duplicate_name(self) -> None:
        router = SkillRouter()
        router.register(TrackingSkill())
        with self.assertRaises(ValueError):
            router.register(TrackingSkill())

    def test_knowledge_router_reads_md_index(self) -> None:
        router = KnowledgeRouter(Settings().knowledge_root)
        self.assertEqual(router.available_entries(), ("framework-overview",))
        self.assertIn("单 Agent", router.get("framework-overview"))

    def test_agent_and_skills_respect_dependency_boundaries(self) -> None:
        guarded_files = [PROJECT_ROOT / "app" / "core" / "agent.py"]
        guarded_files.extend(
            path
            for path in (PROJECT_ROOT / "app" / "skills").glob("*.py")
            if path.name != "__init__.py"
        )

        for path in guarded_files:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            forbidden = [
                name
                for name in imports
                if name.startswith("app.knowledge") or name.startswith("app.tools")
            ]
            self.assertEqual(forbidden, [], f"{path.name}: {forbidden}")


if __name__ == "__main__":
    unittest.main()
