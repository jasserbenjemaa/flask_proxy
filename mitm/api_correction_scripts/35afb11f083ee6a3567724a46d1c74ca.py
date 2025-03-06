import json
import sys

def correct_json(data):
    corrected_data = {}
    corrected_data['id'] = data.get('id')
    corrected_data['name'] = data.get('nme') if data.get('nme') else data.get('name')
    corrected_data['message'] = data.get('messages') if data.get('messages') else data.get('message')
    corrected_data['source'] = data.get('sourc') if data.get('sourc') else data.get('source')
    corrected_data['age'] = data.get('ae') if data.get('ae') else data.get('age')
    
    return corrected_data


if __name__ == "__main__":
    try:
        input_json_str = sys.argv[1]
        input_data = json.loads(input_json_str)
        corrected_data = correct_json(input_data)
        print(json.dumps(corrected_data))
    except (IndexError, json.JSONDecodeError):
        print(json.dumps({"error": "Invalid input. Please provide a valid JSON string as a command-line argument."}))