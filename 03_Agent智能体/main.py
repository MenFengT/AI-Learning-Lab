import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from agents.material_planning_agent import MaterialPlanningAgent


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = PROJECT_ROOT / "test_data" / "施工进度计划（001）.xlsx"


def create_client():
    load_dotenv()
    return OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
    )


def run(file_path):
    agent = MaterialPlanningAgent(create_client())
    result = agent.run(file_path)

    print("施工进度解析完成")
    print("阶段材料分析完成")
    print("月材料计划生成完成")
    return result


def parse_args():
    parser = argparse.ArgumentParser(description="生成建筑项目材料计划")
    parser.add_argument(
        "file_path",
        nargs="?",
        default=str(DEFAULT_INPUT),
        help="施工进度文件路径",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.file_path)
