
import json
import ast
import re
import argparse
import os
from typing import Dict

def infer_schema_from_code(code: str) -> dict:
    """
    Infer a JSON schema from a Flask function body based on key access patterns.
    Supports nested keys like data['name']['first_name'].
    """
    pattern = re.findall(r"data(\[['\"][\w]+['\"]\])+", code)
    schema = {}

    for match in pattern:
        keys = re.findall(r"\[['\"](\w+)['\"]\]", match)
        current = schema
        for i, key in enumerate(keys):
            if i == len(keys) - 1:
                current[key] = "string"
            else:
                current = current.setdefault(key, {})

    return schema

def build_route_schemas(route_data: dict) -> Dict[str, dict]:
    result = {}
    for route, details in route_data.items():
        if "code" in details:
            code = details["code"]
            inferred_schema = infer_schema_from_code(code)
            result[route] = inferred_schema
    return result

def main():
    parser = argparse.ArgumentParser(description="Infer JSON schema from Flask route code.")
    parser.add_argument("json_file", help="Path to the Flask routes JSON file")
    args = parser.parse_args()

    if not os.path.exists(args.json_file):
        print(f"Error: File '{args.json_file}' not found.")
        return

    with open(args.json_file, "r", encoding="utf-8") as f:
        flask_data = json.load(f)

    inferred_schemas = build_route_schemas(flask_data)
    print(json.dumps(inferred_schemas, indent=4))

if __name__ == "__main__":
    main()

