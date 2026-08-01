from parsers.file_parser import parse_file


class FileParserSkill:
    """根据文件类型提取可供进度分析的文本。"""

    def run(self, file_path):
        return parse_file(file_path)
