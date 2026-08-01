from pathlib import Path

from tools.schedule_tool import generate_months



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



    def run(self, progress_data, material_data):


        """
        progress_data:
        施工进度

        material_data:
        阶段材料
        """


        # ======================
        # Python计算月份
        # ======================


        schedule_months = []


        for phase in progress_data["phases"]:


            months = generate_months(

                phase["start"],

                phase["end"]

            )


            schedule_months.append(

                {

                    "phase":phase["name"],

                    "months":months

                }

            )



        # ======================
        # AI整理
        # ======================


        response = self.client.chat.completions.create(


            model="deepseek-chat",


            messages=[


                {

                    "role":"system",

                    "content":self.prompt

                },


                {

                    "role":"user",

                    "content":f"""

施工阶段月份：

{schedule_months}



阶段材料：

{material_data}



请生成月材料计划。

"""

                }

            ]

        )


        return response.choices[0].message.content