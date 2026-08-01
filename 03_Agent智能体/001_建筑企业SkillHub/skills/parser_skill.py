from parsers.file_parser import parse_file

from .base import BaseSkill


class FileParserSkill(BaseSkill):
    """根据文件类型提取可供进度分析的文本。"""

    name = "file_parser"

    def run(self, file_path):
        return parse_file(file_path)
