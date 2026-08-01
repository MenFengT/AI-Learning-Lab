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




class ScheduleMaterialAgent:


    def __init__(self, client):

        self.client = client


        self.prompt = load_prompt(
            "schedule_material_agent.txt"
        )



    def run(self, material_data):


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
以下是阶段材料计划：

{material_data}


请生成月度材料计划。
"""
                }

            ]

        )


        return response.choices[0].message.content