from talkdoc_core.prompts import get_chat_history_to_json_prompt

import json
import logging

from time import time

logging.basicConfig(level=logging.INFO)


def get_json_from_chat_history_agent(gpt, messages_history, orig_parsed_json_fields):

    time_start = time()
    instructions = get_chat_history_to_json_prompt(
        messages_history, orig_parsed_json_fields
    )

    messages = gpt.add_user_prompt([], instructions)

    json_res = gpt.chat(messages, stream=False, json_mode=True)
    json_res = json.loads(json_res)
    logging.info(json_res)
    logging.info(f"Processing time for get_json_from_chat_history_agent: {time() - time_start} seconds")
    return json_res
