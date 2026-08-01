from skills.bootstrap import create_skill_router


class ScheduleMaterialAgent:
    """兼容旧接口：通过 Skill Router 调用月材料计划能力。"""

    def __init__(self, client=None, router=None):
        self.router = router or create_skill_router(client)

    def run(self, progress_data, material_data):
        return self.router.route("monthly_material", progress_data, material_data)
