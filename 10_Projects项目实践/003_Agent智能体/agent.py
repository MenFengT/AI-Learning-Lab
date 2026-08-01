from openai import OpenAI
from dotenv import load_dotenv
import os

from pathlib import Path
from tools import calculate_material
from planner import Planner


load_dotenv()



def load_prompt(file):

    path = Path("prompts") / file

    return path.read_text(
        encoding="utf-8"
    )



class BuildingAgent:


    def __init__(self):

        self.client = OpenAI(

            api_key=os.getenv(
                "DEEPSEEK_API_KEY"
            ),

            base_url=
            "https://api.deepseek.com"
        )


        self.planner = Planner()



    def run(self,task):


        # 任务规划

        plan = self.planner.create_plan(
            task
        )



        # 根据任务选择角色

        if "材料" in task:

            system_prompt = load_prompt(
                "material_agent.txt"
            )


        elif "成本" in task:

            system_prompt = load_prompt(
                "cost_agent.txt"
            )


        else:

            system_prompt = load_prompt(
                "building_agent.txt"
            )



        # 工具计算

        material_result = calculate_material(
            20000,
            20
        )



        response = self.client.chat.completions.create(

            model="deepseek-chat",


            messages=[

                {
                    "role":"system",
                    "content":system_prompt
                },


                {
                    "role":"user",

                    "content":
                    f"""
                    用户需求：

                    {task}


                    Agent规划：

                    {plan}


                    计算数据：

                    {material_result}


                    请生成最终报告。
                    """
                }

            ]

        )


        return response.choices[0].message.content