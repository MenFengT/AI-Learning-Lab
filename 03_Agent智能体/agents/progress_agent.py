# 进度解析Agent
import json

from openai import OpenAI

from pathlib import Path

from parsers.file_parser import parse_file



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




class ProgressAgent:


    def __init__(self,client):

        self.client = client


        self.prompt = load_prompt(
            "progress_agent.txt"
        )



    def run(self,file_path):


        content = parse_file(
            file_path
        )


        response = self.client.chat.completions.create(

            model="deepseek-chat",

            messages=[

                {
                    "role":"system",
                    "content":self.prompt
                },

                {
                    "role":"user",
                    "content":content
                }

            ]

        )


        result = response.choices[0].message.content


        return result