class Planner:

    def create_plan(self, task):

        plan = []

        if "材料" in task or "采购" in task:
            plan.append(
                "调用材料计算工具"
            )

        if "成本" in task:
            plan.append(
                "调用成本分析工具"
            )

        plan.append(
            "整理最终报告"
        )

        return plan