import unittest

from app.core.skill_router import SkillRouter
from app.registry import (
    HealthStatus,
    SkillLifecycleStatus,
    SkillMetadata,
    SkillRegistration,
    SkillRegistry,
)


def registration(
    lifecycle: SkillLifecycleStatus = SkillLifecycleStatus.ACTIVE,
    health: HealthStatus = HealthStatus.HEALTHY,
) -> SkillRegistration:
    return SkillRegistration(
        skill_id="local/probe@0.3.0",
        namespace="local",
        name="probe",
        version="0.3.0",
        manifest_version="0.3",
        metadata=SkillMetadata(
            name="probe",
            version="0.3.0",
            description="精确路由测试",
            inputs=(),
            outputs=(),
        ),
        lifecycle_status=lifecycle,
        health_status=health,
    )


class RouterByIdTests(unittest.TestCase):
    def test_registry_and_router_resolve_stable_skill_id(self) -> None:
        registry = SkillRegistry()
        expected = registration()
        registry.register(expected)

        self.assertIs(registry.get_by_id(expected.skill_id), expected)
        self.assertIs(SkillRouter(registry).select_by_id(expected.skill_id), expected)

    def test_router_rejects_inactive_or_unhealthy_registration(self) -> None:
        for lifecycle, health in (
            (SkillLifecycleStatus.DEPRECATED, HealthStatus.HEALTHY),
            (SkillLifecycleStatus.ACTIVE, HealthStatus.UNHEALTHY),
        ):
            with self.subTest(lifecycle=lifecycle, health=health):
                registry = SkillRegistry()
                item = registration(lifecycle, health)
                registry.register(item)
                with self.assertRaises(LookupError):
                    SkillRouter(registry).select_by_id(item.skill_id)


if __name__ == "__main__":
    unittest.main()
