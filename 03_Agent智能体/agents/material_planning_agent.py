from skills.export_skill import JsonExportSkill
from skills.material_skill import MaterialAnalysisSkill
from skills.parser_skill import FileParserSkill
from skills.progress_skill import ProgressExtractionSkill
from skills.schedule_skill import MonthlyMaterialSkill


class MaterialPlanningAgent:
    """材料计划总调度 Agent，只负责按流程调用 Skills。"""

    def __init__(self, client):
        self.parser_skill = FileParserSkill()
        self.progress_skill = ProgressExtractionSkill(client)
        self.material_skill = MaterialAnalysisSkill(client)
        self.schedule_skill = MonthlyMaterialSkill(client)
        self.export_skill = JsonExportSkill()

    def run(self, file_path, save_outputs=True):
        content = self.parser_skill.run(file_path)
        progress_result = self.progress_skill.run(content)
        material_result = self.material_skill.run(progress_result)
        monthly_result = self.schedule_skill.run(progress_result, material_result)

        if save_outputs:
            self.export_skill.run(progress_result, "progress.json")
            self.export_skill.run(material_result, "material_plan.json")
            self.export_skill.run(monthly_result, "monthly_material_plan.json")

        return {
            "progress": progress_result,
            "material_plan": material_result,
            "monthly_material_plan": monthly_result,
        }
