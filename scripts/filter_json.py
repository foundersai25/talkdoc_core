import json

from talkdoc_core.prompts import filter_json_fields


with open("form_templates/Buergergeld_Antrag.json", "r") as file:
    data = json.load(file)

filtered_data = filter_json_fields(data)
print(filtered_data)

with open("filtered_Buergergeld_Antrag_filtered.json", "w") as file:
    json.dump(filtered_data, file, indent=4)
