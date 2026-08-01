from openai import OpenAI
from dotenv import load_dotenv

import os
import json


from agents.progress_agent import ProgressAgent
from agents.material_agent import MaterialAgent
from agents.schedule_material_agent import ScheduleMaterialAgent


from tools.json_tool import save_json



load_dotenv()



client = OpenAI(

    api_key=os.getenv(
        "DEEPSEEK_API_KEY"
    ),

    base_url="https://api.deepseek.com"

)



# =====================
# 1 进度解析
# =====================


progress_agent = ProgressAgent(
    client
)


file_path = r"E:\施工进度计划（001）.xlsx"



progress_result = progress_agent.run(
    file_path
)



save_json(

    progress_result,

    "progress.json"

)



print(
"施工进度解析完成"
)



# =====================
# 2 阶段材料
# =====================


material_agent = MaterialAgent(
    client
)


material_result = material_agent.run(
    progress_result
)



save_json(

    material_result,

    "material_plan.json"

)


print(
"阶段材料分析完成"
)



# =====================
# 3 月材料计划
# =====================


schedule_agent = ScheduleMaterialAgent(
    client
)


monthly_result = schedule_agent.run(

    progress_result,

    material_result

)


save_json(

    monthly_result,

    "monthly_material_plan.json"

)



print(
"月材料计划生成完成"
)