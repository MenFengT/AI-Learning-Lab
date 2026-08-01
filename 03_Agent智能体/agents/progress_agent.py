from skills.parser_skill import FileParserSkill
from skills.progress_skill import ProgressExtractionSkill


class ProgressAgent:
    """兼容旧接口：只编排文件解析与进度提取 Skill。"""

    def __init__(self, client):
        self.parser_skill = FileParserSkill()
        self.progress_skill = ProgressExtractionSkill(client)

    def run(self, file_path):
        content = self.parser_skill.run(file_path)
        return self.progress_skill.run(content)
