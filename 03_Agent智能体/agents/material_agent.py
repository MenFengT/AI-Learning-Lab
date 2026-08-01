from skills.material_skill import MaterialAnalysisSkill


class MaterialAgent:
    """兼容旧接口：只调用阶段材料分析 Skill。"""

    def __init__(self, client):
        self.material_skill = MaterialAnalysisSkill(client)

    def run(self, progress_data):
        return self.material_skill.run(progress_data)
