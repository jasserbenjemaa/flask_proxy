import json
import sys

def correct_json(input_json):
    corrected_json = {}
    corrected_json['id'] = input_json.get('id')
    corrected_json['name'] = input_json.get('nme')
    corrected_json['message'] = input_json.get('m')
    corrected_json['source'] = input_json.get('srce')
    return corrected_json

if __name__ == "__main__":
    input_str = sys.argv[1]
    input_json = json.loads(input_str)
    corrected_json = correct_json(input_json)
    print(json.dumps(corrected_json))