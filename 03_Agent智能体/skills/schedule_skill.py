import json

from tools.schedule_tool import generate_months

from .prompt_loader import load_prompt


class MonthlyMaterialSkill:
    """计算阶段月份并生成月材料计划。"""

    def __init__(self, client):
        self.client = client
        self.prompt = load_prompt("schedule_material_agent.txt")

    def run(self, progress_data, material_data):
        schedule_months = [
            {
                "phase": phase["name"],
                "months": generate_months(phase["start"], phase["end"]),
            }
            for phase in progress_data["phases"]
        ]

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": self.prompt},
                {
                    "role": "user",
                    "content": (
                        "施工阶段月份：\n\n"
                        f"{json.dumps(schedule_months, ensure_ascii=False)}\n\n"
                        "阶段材料：\n\n"
                        f"{json.dumps(material_data, ensure_ascii=False)}\n\n"
                        "请生成月材料计划。"
                    ),
                },
            ],
        )
        # P1 仅调整职责边界，保留旧版返回原始文本的行为。
        return response.choices[0].message.content
