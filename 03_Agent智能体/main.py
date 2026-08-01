from openai import OpenAI

from dotenv import load_dotenv

import os


from agents.progress_agent import ProgressAgent

from agents.material_agent import MaterialAgent

from agents.schedule_material_agent import ScheduleMaterialAgent



load_dotenv()



client = OpenAI(

    api_key=os.getenv(
        "DEEPSEEK_API_KEY"
    ),

    base_url="https://api.deepseek.com"

)



# ====================
# 1.解析施工进度
# ====================

progress_agent = ProgressAgent(
    client
)


file_path = r"E:\施工进度计划（001）.xlsx"



progress_result = progress_agent.run(
    file_path
)



print("================")
print("施工进度")
print("================")

print(progress_result)



# ====================
# 2.阶段材料分析
# ====================


material_agent = MaterialAgent(
    client
)


material_result = material_agent.run(
    progress_result
)


print("================")
print("阶段材料")
print("================")

print(material_result)



# ====================
# 3.月材料计划
# ====================


schedule_agent = ScheduleMaterialAgent(
    client
)


monthly_result = schedule_agent.run(
    material_result
)



print("================")
print("月材料计划")
print("================")


print(monthly_result)