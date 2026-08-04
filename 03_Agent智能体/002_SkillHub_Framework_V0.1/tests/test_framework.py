import ast
import unittest
from pathlib import Path

from app.config.settings import Settings
from app.core.agent import SkillHubAgent
from app.core.context import TaskContext
from app.core.skill_resolver import InMemorySkillResolver
from app.core.skill_router import SkillRouter
from app.knowledge.knowledge_router import KnowledgeRouter
from app.main import build_agent
from app.registry import (
    DuplicateSkillError,
    HealthStatus,
    SkillLifecycleStatus,
    SkillMetadata,
    SkillRegistration,
    SkillRegistry,
    build_skill_id,
)
from app.runtime.runtime_manager import RuntimeManager
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


def build_registration(skill: BaseSkill) -> SkillRegistration:
    version = "0.2.0"
    return SkillRegistration(
        skill_id=build_skill_id("local", skill.name, version),
        namespace="local",
        name=skill.name,
        version=version,
        manifest_version="0.2",
        metadata=SkillMetadata(
            name=skill.name,
            version=version,
            description=skill.description,
            inputs=(),
            outputs=(),
            keywords=skill.keywords,
        ),
        lifecycle_status=SkillLifecycleStatus.ACTIVE,
        health_status=HealthStatus.HEALTHY,
    )


class SkillHubFrameworkTests(unittest.TestCase):
    def test_minimum_demo_chain(self) -> None:
        result = build_agent().run("请演示任务，返回结果")
        self.assertEqual(result, "DemoSkill 已处理任务：请演示任务；返回结果")

    def test_router_selects_but_does_not_execute(self) -> None:
        skill = TrackingSkill()
        registration = build_registration(skill)
        registry = SkillRegistry()
        registry.register(registration)
        router = SkillRouter(registry)

        selected = router.select("请跟踪这个任务")

        self.assertEqual(selected.skill_id, registration.skill_id)
        self.assertFalse(skill.executed)

    def test_agent_schedules_selected_skill(self) -> None:
        skill = TrackingSkill()
        registration = build_registration(skill)
        registry = SkillRegistry()
        registry.register(registration)
        router = SkillRouter(registry)
        resolver = InMemorySkillResolver({registration.skill_id: skill})

        result = SkillHubAgent(router, RuntimeManager(), resolver).run("跟踪任务")

        self.assertEqual(result, "跟踪任务")
        self.assertTrue(skill.executed)

    def test_registry_rejects_duplicate_name(self) -> None:
        registry = SkillRegistry()
        registration = build_registration(TrackingSkill())
        registry.register(registration)
        with self.assertRaises(DuplicateSkillError):
            registry.register(registration)

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
