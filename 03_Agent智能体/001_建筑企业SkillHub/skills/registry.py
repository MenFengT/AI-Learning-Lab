from .base import BaseSkill


class SkillRegistry:
    """保存并按唯一名称查找 Skill 实例。"""

    def __init__(self):
        self._skills = {}

    def register(self, skill):
        if not isinstance(skill, BaseSkill):
            raise TypeError("skill must inherit BaseSkill")
        if not skill.name:
            raise ValueError("skill.name must not be empty")
        if skill.name in self._skills:
            raise ValueError(f"skill already registered: {skill.name}")
        self._skills[skill.name] = skill
        return skill

    def get(self, name):
        try:
            return self._skills[name]
        except KeyError as exc:
            raise KeyError(f"skill not registered: {name}") from exc

    def names(self):
        return tuple(self._skills)
