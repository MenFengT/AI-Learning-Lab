from skills.bootstrap import create_skill_router


class MaterialPlanningAgent:
    """材料计划总调度 Agent，只通过 Skill Router 编排能力。"""

    def __init__(self, client=None, router=None):
        self.router = router or create_skill_router(client)

    def run(self, file_path, save_outputs=True):
        content = self.router.route("file_parser", file_path)
        progress_result = self.router.route("progress_extraction", content)
        material_result = self.router.route("material_analysis", progress_result)
        monthly_result = self.router.route(
            "monthly_material", progress_result, material_result
        )

        if save_outputs:
            self.router.route("json_export", progress_result, "progress.json")
            self.router.route("json_export", material_result, "material_plan.json")
            self.router.route(
                "json_export", monthly_result, "monthly_material_plan.json"
            )

        return {
            "progress": progress_result,
            "material_plan": material_result,
            "monthly_material_plan": monthly_result,
        }
