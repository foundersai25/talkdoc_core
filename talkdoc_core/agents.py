from talkdoc_core.prompts import get_chat_history_to_json_prompt

import json
import logging

logging.basicConfig(level=logging.INFO)


def get_json_from_chat_history_agent(gpt, messages_history, orig_parsed_json_fields):
    instructions = get_chat_history_to_json_prompt(
        messages_history, orig_parsed_json_fields
    )

    messages = gpt.add_user_prompt([], instructions)

    json_res = gpt.chat(messages, stream=False, json_mode=True)
    json_res = json.loads(json_res)
    logging.info(json_res)
    return json_res
