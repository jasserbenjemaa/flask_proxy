import json
import sys

def correct_json(input_json):
    corrected_json = {}
    if isinstance(input_json, dict):
        if 'id' in input_json:
            corrected_json['id'] = input_json['id']
        if 'nme' in input_json:
            corrected_json['name'] = input_json['nme']
        elif 'name' in input_json:
            corrected_json['name'] = input_json['name']
        if 'meage' in input_json:
            corrected_json['message'] = input_json['meage']
        elif 'message' in input_json:
            corrected_json['message'] = input_json['message']
        if 'source' in input_json:
            corrected_json['source'] = input_json['source']
    return corrected_json

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            input_string = sys.argv[1]
            input_data = json.loads(input_string)
            corrected_data = correct_json(input_data)
            print(json.dumps(corrected_data))
        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid JSON format"}))
    else:
        print(json.dumps({"error": "No input provided"}))