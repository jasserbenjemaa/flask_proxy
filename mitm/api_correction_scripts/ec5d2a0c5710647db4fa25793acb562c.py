import json
import sys

def correct_json(data):
    if 'message' not in data:
        if 'mesage' in data:
            data['message'] = data.pop('mesage')
    return data

if __name__ == "__main__":
    try:
        input_data = json.loads(sys.argv[1])
        corrected_data = correct_json(input_data)
        print(json.dumps(corrected_data))
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON input"}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))