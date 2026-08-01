from skills.bootstrap import create_skill_router


class MaterialAgent:
    """兼容旧接口：通过 Skill Router 调用阶段材料分析能力。"""

    def __init__(self, client=None, router=None):
        self.router = router or create_skill_router(client)

    def run(self, progress_data):
        return self.router.route("material_analysis", progress_data)
