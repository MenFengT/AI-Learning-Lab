from app.config.settings import Settings
from app.core.agent import SkillHubAgent
from app.core.skill_resolver import InMemorySkillResolver
from app.core.skill_router import SkillRouter
from app.registry import (
    HealthStatus,
    SkillLifecycleStatus,
    SkillMetadata,
    SkillRegistration,
    SkillRegistry,
    build_skill_id,
)
from app.runtime.runtime_manager import RuntimeManager
from app.skills.demo_skill import DemoSkill


def build_agent() -> SkillHubAgent:
    """在 Composition Root 集中装配 Registry、Runtime、Router 与 Skill。"""
    skill = DemoSkill()
    version = "0.2.0"
    skill_id = build_skill_id("local", skill.name, version)
    registration = SkillRegistration(
        skill_id=skill_id,
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
    registry = SkillRegistry()
    registry.register(registration)
    router = SkillRouter(registry)
    resolver = InMemorySkillResolver({skill_id: skill})
    return SkillHubAgent(router, RuntimeManager(), resolver)


def main() -> None:
    settings = Settings()
    print(f"{settings.app_name} V{settings.version}")
    user_task = input("请输入任务：")

    try:
        result = build_agent().run(user_task)
    except (ValueError, LookupError) as exc:
        print(f"任务处理失败：{exc}")
        return

    print(result)


if __name__ == "__main__":
    main()
