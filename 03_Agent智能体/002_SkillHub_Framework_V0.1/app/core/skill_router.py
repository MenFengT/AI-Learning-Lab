from app.skills.base_skill import BaseSkill


class SkillRouter:
    """负责 Skill 注册与匹配，不执行具体业务。"""

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        if not skill.name:
            raise ValueError("Skill name 不能为空")
        if skill.name in self._skills:
            raise ValueError(f"Skill 已注册：{skill.name}")
        self._skills[skill.name] = skill

    def select(self, task: str) -> BaseSkill:
        normalized_task = task.lower()
        for skill in self._skills.values():
            if any(keyword.lower() in normalized_task for keyword in skill.keywords):
                return skill
        for skill in self._skills.values():
            if skill.is_default:
                return skill
        raise LookupError(f"没有匹配任务的 Skill：{task}")

    def registered_names(self) -> tuple[str, ...]:
        return tuple(self._skills)
