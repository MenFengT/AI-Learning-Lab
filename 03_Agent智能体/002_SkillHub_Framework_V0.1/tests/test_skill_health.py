import unittest

from app.core.context import TaskContext
from app.registry import (
    HealthStatus,
    SchemaField,
    SkillLifecycleStatus,
    SkillMetadata,
    SkillRegistration,
    build_skill_id,
    check_registration_health,
)
from app.skills.base_skill import BaseSkill


def make_registration() -> SkillRegistration:
    metadata = SkillMetadata(
        name="material_plan",
        version="0.2.0",
        description="生成材料计划",
        inputs=(SchemaField("task", "string", True, "任务描述"),),
        outputs=(SchemaField("result", "string", True, "处理结果"),),
        keywords=("材料计划",),
    )
    return SkillRegistration(
        skill_id=build_skill_id("local", metadata.name, metadata.version),
        namespace="local",
        name=metadata.name,
        version=metadata.version,
        manifest_version="0.1",
        metadata=metadata,
        lifecycle_status=SkillLifecycleStatus.ACTIVE,
    )


class ContractSkill(BaseSkill):
    name = "material_plan"
    description = "健康检查用Skill"
    keywords = ("材料计划",)
    executed = False

    def execute(self, context: TaskContext) -> str:
        type(self).executed = True
        return context.user_task


class WrongNameSkill(ContractSkill):
    name = "wrong_name"


class SkillHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        ContractSkill.executed = False

    def test_valid_descriptor_and_contract_are_healthy_without_execution(self) -> None:
        result = check_registration_health(
            make_registration(), ContractSkill
        )

        self.assertEqual(result.status, HealthStatus.HEALTHY)
        self.assertFalse(ContractSkill.executed)

    def test_contract_mismatch_is_unhealthy(self) -> None:
        result = check_registration_health(
            make_registration(), WrongNameSkill
        )

        self.assertEqual(result.status, HealthStatus.UNHEALTHY)
        self.assertIn("Skill.name与Manifest不一致", result.messages)
        self.assertFalse(ContractSkill.executed)


if __name__ == "__main__":
    unittest.main()
