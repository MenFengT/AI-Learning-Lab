from .export_skill import JsonExportSkill
from .material_skill import MaterialAnalysisSkill
from .parser_skill import FileParserSkill
from .progress_skill import ProgressExtractionSkill
from .registry import SkillRegistry
from .router import SkillRouter
from .schedule_skill import MonthlyMaterialSkill


def create_skill_registry(client):
    """集中装配当前材料计划工作流所需的 Skills。"""
    registry = SkillRegistry()
    registry.register(FileParserSkill())
    registry.register(ProgressExtractionSkill(client))
    registry.register(MaterialAnalysisSkill(client))
    registry.register(MonthlyMaterialSkill(client))
    registry.register(JsonExportSkill())
    return registry


def create_skill_router(client):
    return SkillRouter(create_skill_registry(client))
