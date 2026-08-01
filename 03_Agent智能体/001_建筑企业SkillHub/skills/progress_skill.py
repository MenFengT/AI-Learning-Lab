from .base import BaseSkill
from .llm_response import parse_json_response
from .prompt_loader import load_prompt


class ProgressExtractionSkill(BaseSkill):
    """从已解析的文件文本中提取施工进度 JSON。"""

    name = "progress_extraction"

    def __init__(self, client):
        self.client = client
        self.prompt = load_prompt("progress_agent.txt")

    def run(self, content):
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": content},
            ],
        )
        return parse_json_response(response.choices[0].message.content)
