from openai import OpenAI
from dotenv import load_dotenv
import os


load_dotenv()


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


response = client.chat.completions.create(
    model="gpt-5",
    messages=[
        {
            "role": "user",
            "content": "什么是AI Agent?"
        }
    ]
)


print(response.choices[0].message.content)