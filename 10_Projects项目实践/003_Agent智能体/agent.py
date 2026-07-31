from openai import OpenAI
from dotenv import load_dotenv
import os

from pathlib import Path

from tools import calculate_material


# 加载环境变量
load_dotenv()


client = OpenAI(

    api_key=os.getenv("DEEPSEEK_API_KEY"),

    base_url="https://api.deepseek.com"

)



# 加载角色提示词

def load_prompt(file):

    path = Path("prompts") / file

    return path.read_text(
        encoding="utf-8"
    )




class BuildingAgent:


    def __init__(self):

        self.name = "建筑料账员Agent"


        self.system_prompt = load_prompt(
            "material_agent.txt"
        )



    # 调用材料计算工具

    def calculate_material_plan(
            self,
            area,
            floors
    ):


        result = calculate_material(

            area,

            floors

        )


        return result



    # AI回答功能

    def run(self, task):


        response = client.chat.completions.create(


            model="deepseek-chat",


            messages=[


                {

                    "role":"system",

                    "content":self.system_prompt

                },


                {

                    "role":"user",

                    "content":task

                }

            ]


        )


        return response.choices[0].message.content