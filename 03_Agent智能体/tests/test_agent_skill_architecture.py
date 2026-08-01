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


class FakeCompletions:
    def __init__(self, responses):
        self.responses = iter(responses)

    def create(self, **_kwargs):
        content = next(self.responses)
        message = SimpleNamespace(content=content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeClient:
    def __init__(self, responses):
        completions = FakeCompletions(responses)
        self.chat = SimpleNamespace(completions=completions)


class StubSkill:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def run(self, *args):
        self.calls.append(args)
        return self.result


class AgentSkillArchitectureTests(unittest.TestCase):
    def test_legacy_agents_keep_existing_interfaces(self):
        progress_agent = ProgressAgent(FakeClient([json.dumps(PROGRESS)]))
        progress_agent.parser_skill = StubSkill("parsed content")
        self.assertEqual(progress_agent.run("plan.xlsx"), PROGRESS)

        material_agent = MaterialAgent(FakeClient([json.dumps(MATERIAL)]))
        self.assertEqual(material_agent.run(PROGRESS), MATERIAL)

        schedule_agent = ScheduleMaterialAgent(FakeClient([MONTHLY_TEXT]))
        self.assertEqual(schedule_agent.run(PROGRESS, MATERIAL), MONTHLY_TEXT)

    def test_orchestrator_only_coordinates_skills(self):
        agent = MaterialPlanningAgent(FakeClient([]))
        agent.parser_skill = StubSkill("parsed content")
        agent.progress_skill = StubSkill(PROGRESS)
        agent.material_skill = StubSkill(MATERIAL)
        agent.schedule_skill = StubSkill(MONTHLY_TEXT)
        agent.export_skill = StubSkill(None)

        result = agent.run("plan.xlsx", save_outputs=False)

        self.assertEqual(result["progress"], PROGRESS)
        self.assertEqual(result["material_plan"], MATERIAL)
        self.assertEqual(result["monthly_material_plan"], MONTHLY_TEXT)
        self.assertEqual(agent.progress_skill.calls, [("parsed content",)])
        self.assertEqual(agent.material_skill.calls, [(PROGRESS,)])
        self.assertEqual(agent.schedule_skill.calls, [(PROGRESS, MATERIAL)])

    def test_material_knowledge_is_external_json(self):
        rules_path = PROJECT_ROOT / "knowledge" / "material" / "rules.json"
        rules = json.loads(rules_path.read_text(encoding="utf-8"))
        self.assertEqual(rules["主体结构"]["materials"][0], "混凝土")


if __name__ == "__main__":
    unittest.main()
