from talkdoc_core.prompts import get_system_prompt_for_chat
import openai
from openai import OpenAI
import logging

logging.basicConfig(level=logging.INFO)


class GPTService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)

    def chat(
        self,
        messages,
        model: str = "gpt-4.1",
        stream: bool = True,
        json_mode: bool = False,
    ):
        try:
            params = {
                "model": model,
                "messages": messages,
                "stream": stream,
            }

            if json_mode:
                params["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**params)

            if stream:
                return response

            return response.choices[0].message.content

        except openai.error.OpenAIError as e:
            logging.error(f"OpenAI API error: {e}")
            raise

    def add_system_prompt_for_chat(self, json_fields):
        return [{"role": "system", "content": get_system_prompt_for_chat(json_fields)}]

    def add_user_prompt(self, messages, user_input):
        return messages + [{"role": "user", "content": user_input}]

    def add_assistant_response(self, messages, response):
        return messages + [{"role": "assistant", "content": response}]

    def check_openai_api_key(self):
        try:
            self.client.models.list()
            return True
        except openai.AuthenticationError:
            logging.error("Invalid OpenAI API key")
            return False
