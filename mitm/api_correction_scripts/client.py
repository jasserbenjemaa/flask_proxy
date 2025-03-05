import json
import sys

def correct_json(input_json):
    corrected_json = {}
    if isinstance(input_json, dict):
        if 'name' in input_json:
            corrected_json['name'] = input_json['name']
        elif 'nme' in input_json:
            corrected_json['name'] = input_json['nme']
        if 'message' in input_json:
            corrected_json['message'] = input_json['message']
        elif 'm' in input_json:
            corrected_json['message'] = input_json['m']
        if 'source' in input_json:
            corrected_json['source'] = input_json['source']
        elif 'srce' in input_json:
            corrected_json['source'] = input_json['srce']
        for key, value in input_json.items():
            if key not in ('name', 'nme', 'message', 'm', 'source', 'srce'):
                corrected_json[key] = value
    return corrected_json

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            input_string = sys.argv[1]
            input_data = json.loads(input_string)
            corrected_data = correct_json(input_data)
            print(json.dumps(corrected_data))
        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid JSON"}))
    else:
        print(json.dumps({"error": "No input provided"}))