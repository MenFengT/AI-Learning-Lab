from skills.bootstrap import create_skill_router


class ProgressAgent:
    """兼容旧接口：通过 Skill Router 编排文件解析与进度提取。"""

    def __init__(self, client=None, router=None):
        self.router = router or create_skill_router(client)

    def run(self, file_path):
        content = self.router.route("file_parser", file_path)
        return self.router.route("progress_extraction", content)
