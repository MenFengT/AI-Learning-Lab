from openai import OpenAI
from dotenv import load_dotenv

import os


from agents.progress_agent import ProgressAgent



load_dotenv()



client = OpenAI(

    api_key=os.getenv(
        "DEEPSEEK_API_KEY"
    ),

    base_url="https://api.deepseek.com"

)



agent = ProgressAgent(
    client
)



# 施工进度计划文件

file_path = r"E:\施工进度计划（001）.xlsx"



result = agent.run(
    file_path
)



print("====================")
print("施工进度解析结果")
print("====================")


print(result)