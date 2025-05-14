
#!/usr/bin/env python3
import sys
import json

def fix_data(data):
    # Similarity score: 0.952
    try:
        if 'secod_name' in data['name']:
            data['name']['second_name'] = data['name']['secod_name']
            # Optional: remove the incorrect field after copying its value
            del data['name']['secod_name']
    except (KeyError, TypeError):
        pass

    # Similarity score: 0.947
    try:
        if 'fist_name' in data['name']:
            data['name']['first_name'] = data['name']['fist_name']
            # Optional: remove the incorrect field after copying its value
            del data['name']['fist_name']
    except (KeyError, TypeError):
        pass
    return data

def get_nested_value(data, path_parts):
    
    current = data
    for part in path_parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current

def set_nested_value(data, path_parts, value):
    
    current = data
    for part in path_parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    current[path_parts[-1]] = value

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py '<json_string>'")
        sys.exit(1)
        
    input_data = sys.argv[1]
    try:
        data = json.loads(input_data)
        fixed_data = fix_data(data)
        print(json.dumps(fixed_data, indent=2))
    except json.JSONDecodeError:
        print("Error: Invalid JSON format.")
