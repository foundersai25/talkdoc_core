from core.talkdoc_core.prompts import get_chat_history_to_json_prompt

import json
import logging
import os
import re
import requests
from agno.tools import tool

logging.basicConfig(level=logging.INFO)


# Standalone Tool function for Agno (outside the class)
@tool(
    name="validate_address",
    description="Validates an address using Google Maps API and returns the raw response.",
    show_result=False
)
def validate_address(address_string: str) -> str:
    """Makes Google Maps API call and returns the response."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return json.dumps({"error": "API Key not available"})
    
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': address_string,
            'key': api_key,
            'language': 'de',
            'region': 'de'
        }
        
        response = requests.get(url, params=params)
        return json.dumps(response.json(), ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool(
    name="validate_regex",
    description="Validates a string against a regex pattern and returns detailed match information.",
    show_result=False
)
def validate_regex(input_string: str, regex_pattern: str) -> str:
    """Validates a string against a regex pattern and returns match details."""
    try:
        # Compile the regex pattern
        compiled_pattern = re.compile(regex_pattern)
        
        # Perform both match and search operations
        match_result = compiled_pattern.match(input_string)
        search_result = compiled_pattern.search(input_string)
        
        # Find all matches
        all_matches = compiled_pattern.findall(input_string)
        
        # Find all match objects with positions
        all_match_objects = list(compiled_pattern.finditer(input_string))
        
        # Build compact result dictionary
        result = {
            "match_found": match_result is not None,
            "search_found": search_result is not None,
            "match_count": len(all_match_objects),
            "first_match": match_result.group() if match_result else None,
            "all_matches": all_matches[:5] if len(all_matches) > 5 else all_matches  # Limit to first 5 matches
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except re.error as e:
        # Handle invalid regex patterns
        error_result = {
            "match_found": False,
            "search_found": False,
            "match_count": 0,
            "first_match": None,
            "all_matches": [],
            "error": f"Invalid regex: {str(e)}"
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        # Handle other unexpected errors
        error_result = {
            "match_found": False,
            "search_found": False,
            "match_count": 0,
            "first_match": None,
            "all_matches": [],
            "error": f"Error: {str(e)}"
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


# Helper function for API key validation
def check_google_maps_api_key(api_key: str = None) -> bool:
    """Checks if the Google Maps API key is valid."""
    test_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
    if not test_key:
        return False
    return len(test_key) > 10 and test_key.startswith(('AIza', 'Goog'))


def get_json_from_chat_history_agent(gpt, messages_history, orig_parsed_json_fields):
    instructions = get_chat_history_to_json_prompt(
        messages_history, orig_parsed_json_fields
    )

    messages = gpt.add_user_prompt([], instructions)

    json_res = gpt.chat(messages, stream=False, json_mode=True)
    json_res = json.loads(json_res)
    logging.info(json_res)
    return json_res
