from skills.schedule_skill import MonthlyMaterialSkill


class ScheduleMaterialAgent:
    """兼容旧接口：只调用月材料计划 Skill。"""

    def __init__(self, client):
        self.schedule_skill = MonthlyMaterialSkill(client)

    def run(self, progress_data, material_data):
        return self.schedule_skill.run(progress_data, material_data)
