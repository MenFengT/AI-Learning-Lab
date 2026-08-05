import json

from .base import BaseSkill
from .llm_response import parse_json_response
from .prompt_loader import PROJECT_ROOT, load_prompt


class MaterialAnalysisSkill(BaseSkill):
    """根据进度数据和独立知识规则生成阶段材料计划。"""

    name = "material_analysis"

    def __init__(self, client):
        self.client = client
        self.prompt = load_prompt("material_agent.txt")
        rules_path = PROJECT_ROOT / "knowledge" / "material" / "rules.json"
        self.rules = json.loads(rules_path.read_text(encoding="utf-8"))

    def run(self, progress_data):
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": self.prompt},
                {
                    "role": "user",
                    "content": (
                        "以下是施工进度解析结果：\n\n"
                        f"{json.dumps(progress_data, ensure_ascii=False)}\n\n"
                        "以下是施工阶段与材料知识：\n\n"
                        f"{json.dumps(self.rules, ensure_ascii=False)}\n\n"
                        "请分析全部施工阶段，生成完整材料需求计划。"
                    ),
                },
            ],
        )
        return parse_json_response(response.choices[0].message.content)
