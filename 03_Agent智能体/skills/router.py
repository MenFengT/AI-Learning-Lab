class SkillRouter:
    """Agent 与具体 Skill 之间的统一调用入口。"""

    def __init__(self, registry):
        self.registry = registry

    def route(self, skill_name, *args, **kwargs):
        skill = self.registry.get(skill_name)
        return skill.run(*args, **kwargs)

    def available_skills(self):
        return self.registry.names()
