from tools.json_tool import save_json


class JsonExportSkill:
    """把工作流结果保存到现有 outputs 目录。"""

    def run(self, data, filename):
        return save_json(data, filename)
