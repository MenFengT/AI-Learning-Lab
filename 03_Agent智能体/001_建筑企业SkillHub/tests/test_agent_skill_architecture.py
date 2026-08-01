import ast
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.material_agent import MaterialAgent
from agents.material_planning_agent import MaterialPlanningAgent
from agents.progress_agent import ProgressAgent
from agents.schedule_material_agent import ScheduleMaterialAgent
from skills.base import BaseSkill
from skills.bootstrap import create_skill_registry
from skills.registry import SkillRegistry
from skills.router import SkillRouter


PROGRESS = {
    "project_name": None,
    "start_date": "2026-01-01",
    "end_date": "2026-02-01",
    "phases": [
        {"name": "土方工程", "start": "2026-01-01", "end": "2026-02-01"}
    ],
}
MATERIAL = {
    "plans": [
        {
            "phase": "土方工程",
            "materials": [{"name": "回填材料", "reason": "用于回填"}],
        }
    ]
}
MONTHLY_TEXT = json.dumps(
    {
        "monthly_plan": [
            {
                "month": "2026-01",
                "materials": [{"name": "回填材料", "phase": "土方工程"}],
            }
        ]
    },
    ensure_ascii=False,
)


class EchoSkill(BaseSkill):
    name = "echo"

    def run(self, value):
        return value


class FakeCompletions:
    def __init__(self, responses):
        self.responses = iter(responses)

    def create(self, **_kwargs):
        message = SimpleNamespace(content=next(self.responses))
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeClient:
    def __init__(self, responses):
        completions = FakeCompletions(responses)
        self.chat = SimpleNamespace(completions=completions)


class FakeRouter:
    def __init__(self, results):
        self.results = {name: iter(values) for name, values in results.items()}
        self.calls = []

    def route(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        return next(self.results[name])


class FrameworkTests(unittest.TestCase):
    def test_base_skill_is_abstract(self):
        with self.assertRaises(TypeError):
            BaseSkill()

    def test_registry_and_router(self):
        registry = SkillRegistry()
        skill = registry.register(EchoSkill())
        router = SkillRouter(registry)

        self.assertIs(registry.get("echo"), skill)
        self.assertEqual(registry.names(), ("echo",))
        self.assertEqual(router.route("echo", "value"), "value")

        with self.assertRaises(ValueError):
            registry.register(EchoSkill())
        with self.assertRaises(KeyError):
            router.route("missing")
        with self.assertRaises(TypeError):
            registry.register(object())

    def test_default_registry_contains_current_skills(self):
        registry = create_skill_registry(FakeClient([]))
        self.assertEqual(
            registry.names(),
            (
                "file_parser",
                "progress_extraction",
                "material_analysis",
                "monthly_material",
                "json_export",
            ),
        )


class AgentRouterTests(unittest.TestCase):
    def test_material_planning_agent_routes_without_changing_results(self):
        router = FakeRouter(
            {
                "file_parser": ["parsed content"],
                "progress_extraction": [PROGRESS],
                "material_analysis": [MATERIAL],
                "monthly_material": [MONTHLY_TEXT],
                "json_export": [None, None, None],
            }
        )
        result = MaterialPlanningAgent(router=router).run("plan.xlsx")

        self.assertEqual(
            result,
            {
                "progress": PROGRESS,
                "material_plan": MATERIAL,
                "monthly_material_plan": MONTHLY_TEXT,
            },
        )
        self.assertEqual(
            [call[0] for call in router.calls],
            [
                "file_parser",
                "progress_extraction",
                "material_analysis",
                "monthly_material",
                "json_export",
                "json_export",
                "json_export",
            ],
        )
        self.assertEqual(
            [call[1][1] for call in router.calls[-3:]],
            ["progress.json", "material_plan.json", "monthly_material_plan.json"],
        )

    def test_legacy_agents_keep_existing_run_interfaces(self):
        progress_router = FakeRouter(
            {"file_parser": ["parsed"], "progress_extraction": [PROGRESS]}
        )
        self.assertEqual(ProgressAgent(router=progress_router).run("plan.xlsx"), PROGRESS)

        material_router = FakeRouter({"material_analysis": [MATERIAL]})
        self.assertEqual(MaterialAgent(router=material_router).run(PROGRESS), MATERIAL)

        schedule_router = FakeRouter({"monthly_material": [MONTHLY_TEXT]})
        self.assertEqual(
            ScheduleMaterialAgent(router=schedule_router).run(PROGRESS, MATERIAL),
            MONTHLY_TEXT,
        )

    def test_legacy_client_constructor_uses_default_registry(self):
        material_client = FakeClient([json.dumps(MATERIAL, ensure_ascii=False)])
        self.assertEqual(MaterialAgent(material_client).run(PROGRESS), MATERIAL)

        schedule_client = FakeClient([MONTHLY_TEXT])
        self.assertEqual(
            ScheduleMaterialAgent(schedule_client).run(PROGRESS, MATERIAL),
            MONTHLY_TEXT,
        )

    def test_agents_do_not_instantiate_concrete_skills(self):
        for path in (PROJECT_ROOT / "agents").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            concrete_calls = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id.endswith("Skill"):
                        concrete_calls.append(node.func.id)
            self.assertEqual(concrete_calls, [], f"{path.name}: {concrete_calls}")

    def test_material_knowledge_is_external_json(self):
        rules_path = PROJECT_ROOT / "knowledge" / "material" / "rules.json"
        rules = json.loads(rules_path.read_text(encoding="utf-8"))
        self.assertEqual(rules["主体结构"]["materials"][0], "混凝土")


if __name__ == "__main__":
    unittest.main()
