import json
import re

from pathlib import Path



def load_prompt(filename):

    path = (
        Path(__file__)
        .parent
        .parent
        /
        "prompts"
        /
        filename
    )


    return path.read_text(
        encoding="utf-8"
    )




class MaterialAgent:


    def __init__(self, client):

        self.client = client


        self.prompt = load_prompt(
            "material_agent.txt"
        )



    def run(self, progress_data):


        response = self.client.chat.completions.create(


            model="deepseek-chat",


            messages=[


                {

                    "role":"system",

                    "content":self.prompt

                },


                {

                    "role":"user",

                    "content":
                    f"""
以下是施工进度解析结果：

{progress_data}


请分析全部施工阶段，
生成完整材料需求计划。
"""

                }

            ]

        )

        result = response.choices[0].message.content

        result = re.sub(
            r"```json|```",
            "",
            result
        ).strip()

        data = json.loads(
            result
        )

        return data