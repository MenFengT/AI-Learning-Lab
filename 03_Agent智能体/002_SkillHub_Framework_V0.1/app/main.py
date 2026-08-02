from app.config.settings import Settings
from app.core.agent import SkillHubAgent
from app.core.skill_router import SkillRouter
from app.skills.demo_skill import DemoSkill


def build_agent() -> SkillHubAgent:
    """在启动层集中装配 Router、Skill 与唯一 Agent。"""
    router = SkillRouter()
    router.register(DemoSkill())
    return SkillHubAgent(router)


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
