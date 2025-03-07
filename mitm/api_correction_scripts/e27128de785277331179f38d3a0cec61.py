import json
import sys

def correct_json(data):
    corrected_data = {}
    if isinstance(data, dict):
        corrected_data['name'] = data.get('name') or data.get('username') or data.get('user_name')
        corrected_data['message'] = data.get('message') or data.get('msg') or data.get('content')
        corrected_data['source'] = data.get('source') or data.get('origin') or data.get('src')
        corrected_data['age'] = data.get('age') or data.get('ages') or data.get('years')
        for key, value in data.items():
          if key not in ('name', 'username', 'user_name', 'message', 'msg', 'content', 'source', 'origin', 'src', 'age', 'ages', 'years'):
            corrected_data[key] = value
    return corrected_data

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            input_json = sys.argv[1]
            data = json.loads(input_json)
            corrected_data = correct_json(data)
            print(json.dumps(corrected_data))
        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid JSON format"}))
        except Exception as e:
            print(json.dumps({"error": str(e)}))
    else:
        print(json.dumps({"error": "No JSON input provided"}))