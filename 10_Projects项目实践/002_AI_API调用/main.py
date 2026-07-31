from openai import OpenAI
from dotenv import load_dotenv
import os


load_dotenv()


client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


def ask_ai(question):

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role":"user",
                "content":question
            }
        ]
    )

    return response.choices[0].message.content



if __name__ == "__main__":

    result = ask_ai(
        "什么是建筑行业AI Agent?"
    )

    print(result)