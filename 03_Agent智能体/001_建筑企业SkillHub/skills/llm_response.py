import json
import re


def parse_json_response(content):
    """将 LLM 返回的 JSON 或 Markdown JSON 代码块转换为字典。"""
    cleaned = re.sub(r"```json|```", "", content).strip()
    return json.loads(cleaned)
