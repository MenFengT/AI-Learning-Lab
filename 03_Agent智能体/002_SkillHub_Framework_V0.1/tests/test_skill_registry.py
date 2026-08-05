import unittest

from app.registry import (
    ActiveVersionConflictError,
    DuplicateSkillError,
    HealthStatus,
    SchemaField,
    SkillLifecycleStatus,
    SkillMetadata,
    SkillNotFoundError,
    SkillRegistration,
    SkillRegistry,
    build_skill_id,
)


def make_registration(
    version: str,
    *,
    lifecycle: SkillLifecycleStatus = SkillLifecycleStatus.ACTIVE,
    health: HealthStatus = HealthStatus.HEALTHY,
) -> SkillRegistration:
    metadata = SkillMetadata(
        name="material_plan",
        version=version,
        description="生成材料计划",
        inputs=(SchemaField("task", "string", True, "任务描述"),),
        outputs=(SchemaField("result", "string", True, "处理结果"),),
        permissions=frozenset({"FILE_READ"}),
        keywords=("材料计划", "月材料"),
    )
    return SkillRegistration(
        skill_id=build_skill_id("local", metadata.name, version),
        namespace="local",
        name=metadata.name,
        version=version,
        manifest_version="0.1",
        metadata=metadata,
        lifecycle_status=lifecycle,
        health_status=health,
    )


class SkillRegistryTests(unittest.TestCase):
    def test_register_and_get_by_stable_identity(self) -> None:
        registry = SkillRegistry()
        registration = make_registration("0.2.0")

        registry.register(registration)

        self.assertEqual(registration.skill_id, "local/material_plan@0.2.0")
        self.assertIs(registry.get("material_plan", "0.2.0"), registration)

    def test_duplicate_registration_is_rejected(self) -> None:
        registry = SkillRegistry()
        registration = make_registration("0.2.0")
        registry.register(registration)

        with self.assertRaises(DuplicateSkillError):
            registry.register(registration)

    def test_multiple_versions_and_single_active_policy(self) -> None:
        registry = SkillRegistry()
        old = make_registration(
            "0.1.0", lifecycle=SkillLifecycleStatus.DEPRECATED
        )
        current = make_registration("0.2.0")
        registry.register(old)
        registry.register(current)

        self.assertEqual(
            [item.version for item in registry.list_by_name("material_plan")],
            ["0.1.0", "0.2.0"],
        )
        with self.assertRaises(ActiveVersionConflictError):
            registry.register(make_registration("0.3.0"))

    def test_query_candidates_and_unregister(self) -> None:
        registry = SkillRegistry()
        registration = make_registration("0.2.0")
        registry.register(registration)

        self.assertEqual(
            registry.find_candidates("请生成月材料计划"), (registration,)
        )
        self.assertEqual(registry.unregister(registration.skill_id), registration)
        with self.assertRaises(SkillNotFoundError):
            registry.get("material_plan", "0.2.0")

    def test_registration_rejects_random_or_inconsistent_id(self) -> None:
        valid = make_registration("0.2.0")
        with self.assertRaises(ValueError):
            SkillRegistration(
                skill_id="random-uuid",
                namespace=valid.namespace,
                name=valid.name,
                version=valid.version,
                manifest_version=valid.manifest_version,
                metadata=valid.metadata,
                lifecycle_status=valid.lifecycle_status,
            )


if __name__ == "__main__":
    unittest.main()
