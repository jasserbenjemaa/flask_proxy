import json
import sys

def correct_json(data):
    corrected_data = {}
    name_keys = ["name", "nme", "nam"]
    message_keys = ["message", "messages", "msg"]
    source_keys = ["source", "sourc", "src"]
    age_keys = ["age", "ae", "ag"]

    for key in data:
        if key in name_keys:
            corrected_data["name"] = data[key]
        elif key in message_keys:
            corrected_data["message"] = data[key]
        elif key in source_keys:
            corrected_data["source"] = data[key]
        elif key in age_keys:
            corrected_data["age"] = data[key]
        else:
            corrected_data[key] = data[key]

    if "name" not in corrected_data and any(k in data for k in name_keys):
        for k in name_keys:
            if k in data:
                corrected_data["name"] = data[k]
                break

    if "message" not in corrected_data and any(k in data for k in message_keys):
        for k in message_keys:
            if k in data:
                corrected_data["message"] = data[k]
                break

    if "source" not in corrected_data and any(k in data for k in source_keys):
        for k in source_keys:
            if k in data:
                corrected_data["source"] = data[k]
                break

    if "age" not in corrected_data and any(k in data for k in age_keys):
        for k in age_keys:
            if k in data:
                corrected_data["age"] = data[k]
                break


    return corrected_data

if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_json_string = sys.argv[1]
        try:
            input_data = json.loads(input_json_string)
            corrected_data = correct_json(input_data)
            print(json.dumps(corrected_data))
        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid JSON format"}))
    else:
        print(json.dumps({"error": "No JSON input provided"}))