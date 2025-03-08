import sys
import json

def fix_data(data):
    fixed_data = {}
    fixed_data['name'] = data.get('nme', '')
    fixed_data['message'] = data.get('messages', '')
    fixed_data['source'] = data.get('sourc', '')
    fixed_data['age'] = data.get('ae', '')
    return fixed_data

if __name__ == "__main__":
    input_data = sys.argv[1]
    try:
        data = json.loads(input_data)
        fixed_data = fix_data(data)
        print(json.dumps(fixed_data))
    except json.JSONDecodeError:
        print("Error: Invalid JSON format.")