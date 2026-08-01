from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_prompt(filename):
    """从项目 prompts 目录读取提示词。"""
    return (PROJECT_ROOT / "prompts" / filename).read_text(encoding="utf-8")
