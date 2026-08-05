from tools.json_tool import save_json

from .base import BaseSkill


class JsonExportSkill(BaseSkill):
    """把工作流结果保存到现有 outputs 目录。"""

    name = "json_export"

    def run(self, data, filename):
        return save_json(data, filename)
