import json
import re
import ast
from typing import Dict, Any, List, Optional

def extract_form_keys(code_str: str) -> Dict[str, str]:
    """Extract form keys from Flask request.form access patterns."""
    schema = {}
    
    # Look for data["key"] pattern
    data_key_pattern = re.compile(r'data\["([^"]+)"\]')
    data_keys = data_key_pattern.findall(code_str)
    
    # Look for data.get('key') pattern
    data_get_pattern = re.compile(r'data\.get\([\'"]([^\'"]+)[\'"]')
    data_get_keys = data_get_pattern.findall(code_str)
    
    # Combine unique keys
    all_keys = set(data_keys + data_get_keys)
    
    # Create schema with string type for all fields (default)
    for key in all_keys:
        schema[key] = {"type": "string"}
    
    return schema

def extract_json_keys(code_str: str) -> Dict[str, str]:
    """Extract keys from request.get_json() access patterns."""
    schema = {}
    
    # Look for data['key'] pattern
    data_key_pattern = re.compile(r'data\[[\'"]([\w]+)[\'"]\]')
    data_keys = data_key_pattern.findall(code_str)
    
    # Look for data.get('key') pattern
    data_get_pattern = re.compile(r'data\.get\([\'"]([^\'"]+)[\'"]')
    data_get_keys = data_get_pattern.findall(code_str)
    
    # Combine unique keys
    all_keys = set(data_keys + data_get_keys)
    
    # Create schema with string type for all fields (default)
    for key in all_keys:
        schema[key] = {"type": "string"}
    
    # Try to infer types from usage context
    infer_types(code_str, schema)
    
    return schema

def infer_types(code_str: str, schema: Dict[str, Dict[str, str]]) -> None:
    """
    Attempt to infer data types from usage context.
    Updates schema dict in place.
    """
    # Look for int() conversions
    int_pattern = re.compile(r'int\(data\[[\'"]([^\'"]+)[\'"]\]\)')
    int_keys = int_pattern.findall(code_str)
    
    # Look for float() conversions
    float_pattern = re.compile(r'float\(data\[[\'"]([^\'"]+)[\'"]\]\)')
    float_keys = float_pattern.findall(code_str)
    
    # Look for bool evaluations
    bool_pattern = re.compile(r'(if|while)\s+data\[[\'"]([^\'"]+)[\'"]\]')
    bool_keys = [match[1] for match in bool_pattern.findall(code_str)]
    
    # Update schema with inferred types
    for key in int_keys:
        if key in schema:
            schema[key]["type"] = "integer"
    
    for key in float_keys:
        if key in schema:
            schema[key]["type"] = "number"
    
    for key in bool_keys:
        if key in schema:
            schema[key]["type"] = "boolean"

def analyze_route_handler(code_str: str) -> Dict[str, Any]:
    """Analyze a Flask route handler to extract request schema."""
    schema = {"type": "object", "properties": {}, "required": []}
    
    # Determine if it's using form data or JSON
    if "request.form" in code_str:
        # Form data
        schema["properties"] = extract_form_keys(code_str)
        schema["requestType"] = "form"
    elif "request.get_json()" in code_str or "request.json" in code_str:
        # JSON data
        schema["properties"] = extract_json_keys(code_str)
        schema["requestType"] = "json"
    else:
        # Query parameters or no request body
        schema["requestType"] = "query/none"
    
    # Attempt to determine required fields
    # Look for keys that are accessed without .get() which might throw KeyError
    direct_access_pattern = re.compile(r'data\[[\'"]([\w]+)[\'"]\]')
    potentially_required = direct_access_pattern.findall(code_str)
    
    # If they're also in our properties, mark them as required
    for key in potentially_required:
        if key in schema["properties"]:
            schema["required"].append(key)
    
    return schema

def extract_schemas_from_routes_file(file_path: str) -> Dict[str, Any]:
    """
    Extract request schemas from a flask_routes.json file.
    
    Args:
        file_path: Path to the flask_routes.json file
        
    Returns:
        Dictionary mapping route paths to their request schemas
    """
    with open(file_path, 'r') as f:
        routes_data = json.load(f)
    
    schemas = {}
    
    for route_path, route_info in routes_data.items():
        # Only process routes that accept data (POST, PUT, PATCH)
        if any(method in ['POST', 'PUT', 'PATCH'] for method in route_info.get('methods', [])):
            code = route_info.get('code', '')
            
            # Skip if no code available
            if not code:
                continue
            
            try:
                schema = analyze_route_handler(code)
                schemas[route_path] = {
                    "methods": route_info.get('methods', []),
                    "function": route_info.get('function', ''),
                    "requestSchema": schema
                }
            except Exception as e:
                print(f"Error analyzing route {route_path}: {str(e)}")
                schemas[route_path] = {
                    "methods": route_info.get('methods', []),
                    "function": route_info.get('function', ''),
                    "error": str(e)
                }
    
    return schemas

def create_json_schema_docs(schemas: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert the extracted schemas to proper JSON Schema format.
    
    Args:
        schemas: Dictionary of route schemas
        
    Returns:
        Dictionary with properly formatted JSON Schema documents
    """
    json_schemas = {}
    
    for route, info in schemas.items():
        if "requestSchema" not in info:
            continue
            
        request_schema = info["requestSchema"]
        
        # Create proper JSON Schema document
        json_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": f"{info['function']} Request Schema",
            "description": f"Schema for {', '.join(info['methods'])} request to {route}",
            "type": "object"
        }
        
        # Add properties
        if "properties" in request_schema:
            json_schema["properties"] = request_schema["properties"]
            
        # Add required fields if any
        if "required" in request_schema and request_schema["required"]:
            json_schema["required"] = request_schema["required"]
            
        json_schemas[route] = json_schema
    
    return json_schemas

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = input("Enter the path to flask_routes.json: ")
    
    # Extract schemas
    schemas = extract_schemas_from_routes_file(file_path)
    
    # Convert to JSON Schema format
    json_schemas = create_json_schema_docs(schemas)
    
    # Save to file
    output_file = "request_schemas.json"
    with open(output_file, 'w') as f:
        json.dump(json_schemas, f, indent=4)
    
    print(f"Generated request schemas for {len(json_schemas)} routes.")
    print(f"Results saved to {output_file}")
    
    # Print summary
    print("\nExtracted request schemas:")
    for route, schema in json_schemas.items():
        methods = schemas[route]["methods"]
        print(f"{', '.join(methods).ljust(15)} {route.ljust(30)}")
        
        # Print properties
        if "properties" in schema:
            for prop, details in schema["properties"].items():
                prop_type = details.get("type", "string")
                required = "*" if "required" in schema and prop in schema["required"] else " "
                print(f"  {required} {prop.ljust(20)} {prop_type}")
