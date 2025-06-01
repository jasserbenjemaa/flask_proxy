from mitmproxy import ctx
import os
import subprocess
import traceback
import json
import hashlib

def get_file_path(flow, backend_json):
    server_url = flow.request.url
    
    method = flow.request.method
    
    def extract_all_fields(data, prefix=""):
        """Recursively extract all fields and sub-fields from a dictionary"""
        result = []
        if isinstance(data, dict):
            for key, value in sorted(data.items()):
                field_name = f"{prefix}_{key}" if prefix else key
                result.append(field_name)
                if isinstance(value, (dict, list)):
                    result.extend(extract_all_fields(value, field_name))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    result.extend(extract_all_fields(item, f"{prefix}_{i}" if prefix else str(i)))
        return result
    
    try:
        client_req = json.loads(flow.request.content.decode('utf-8'))
        
        # Extract all fields from client_req and backend_json
        client_fields = extract_all_fields(client_req)
        backend_fields = extract_all_fields(backend_json)
        
        # Combine all fields for the filename
        all_fields = sorted(set(client_fields + backend_fields))
        str_key = "_".join(all_fields)
        
        # Generate filename based on URL, method, and fields
        file_name = f"{str(server_url).replace('http://','').replace('/','_')}_{method}_{str_key}"
        hash_file_name = hashlib.md5(file_name.encode()).hexdigest()
        return f"api_correction_scripts/{hash_file_name}.py"
    except Exception as e:
        ctx.log.error(f"Error generating file path: {e}")
        # Fallback to a simpler hash if there's an error
        simple_name = f"{server_url}_{method}"
        hash_file_name = hashlib.md5(simple_name.encode()).hexdigest()
        return f"api_correction_scripts/fallback_{hash_file_name}.py"

def fix_api(api, file_path):
    try:
        ctx.log.info(f"Original request: {api}")
        if os.path.exists(file_path):
            # Add timeout to prevent hanging
            process = subprocess.run(
                ["python3", file_path, api],
                capture_output=True,
                text=True,
                timeout=5
            )

            if process.returncode != 0:
                ctx.log.error(f"Script failed with error: {process.stderr}")
                return api

            fixed_api = process.stdout
            ctx.log.info(f"Fixed request: {fixed_api}")
            return fixed_api
        else:
            ctx.log.info("Correction script not found")
    except subprocess.TimeoutExpired:
        ctx.log.error(f"Script execution timed out: {file_path}")
    except Exception :
        error_trace = traceback.format_exc()
        ctx.log.error(f"Error in fix_api: {error_trace}")
    return api


from pathlib import Path

def read_json_file(file_name: str, search_dir: str = '.') :
    """
    Searches for a JSON file in a directory tree and reads its contents.

    Parameters:
        file_name (str): Name of the JSON file to find.
        search_dir (str): Directory to start the search from.

    Returns:
        dict: Parsed JSON content if successful, otherwise an empty dict.
    """
    search_path = Path(search_dir)

    try:
        file_path = next(search_path.rglob(file_name))
    except StopIteration:
        print(f"Error: '{file_name}' not found in '{search_dir}'.")
        return {}

    try:
        with file_path.open('r', encoding='utf-8') as file:
            data = json.load(file)
            print(f"File found and loaded: {file_path.resolve()}")
            return data if isinstance(data, dict) else {}
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format. {e}")
    except Exception as e:
        print(f"Error reading file: {e}")

    return {}

def generate_error_documentation(url_path, status_code, method, field_differences):
    """
    Generate standardized error documentation for API endpoints.

    Args:
        url_path (str): The API endpoint path (e.g., 'api/home')
        status_code (int): HTTP status code (e.g., 400, 404, 500)
        method (str): HTTP method (e.g., 'GET', 'POST')
        field_differences (dict): Dictionary of field differences between client and server
            - Keys with 'Missing in B' value exist in server schema but not in client request
            - Keys with 'Missing in A' value exist in client request but not in server schema

    Returns:
        dict: Structured error documentation
    """
    # Dictionary to map status codes to standard error messages
    status_messages = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        409: "Conflict",
        429: "Too Many Requests",
        500: "Internal Server Error",
        503: "Service Unavailable"
    }

    # Get default message based on status code
    default_message = status_messages.get(status_code, "Unknown Error")

    # Generate description based on status code
    descriptions = {
        400: "The API request is malformed or contains invalid parameters.",
        401: "The provided credentials are invalid or missing.",
        403: "You don't have permission to access this resource.",
        404: "The requested resource could not be found.",
        409: "A conflict occurred with the current state of the resource.",
        429: "You have exceeded the rate limit for requests.",
        500: "An unexpected error occurred while processing the request.",
        503: "The service is temporarily unavailable or undergoing maintenance."
    }
    description = descriptions.get(status_code, "An error occurred while processing your request.")

    # Process field differences to generate cause information
    cause_parts = []

    # Fields missing in client request (exist in server schema)
    missing_in_request = [field for field, value in field_differences.items() if value == "Missing in B"]
    if missing_in_request:
        missing_fields_str = ", ".join(f"'{field}'" for field in missing_in_request)
        cause_parts.append(f"Missing required field(s): {missing_fields_str}")

    # Extra fields in client request (don't exist in server schema)
    extra_in_request = [field for field, value in field_differences.items() if value == "Missing in A"]
    if extra_in_request:
        extra_fields_str = ", ".join(f"'{field}'" for field in extra_in_request)
        cause_parts.append(f"Unexpected field(s): {extra_fields_str}")

    # Combine all cause parts
    cause = ". ".join(cause_parts) if cause_parts else "Unknown cause."

    # Build and return the error documentation
    error_doc = {
        url_path: {
            "status_code": status_code,
            "method": method,
            "error": {
                "message": default_message,
                "description": description,
                "cause": cause
            }
        }
    }

    return error_doc


def save_to_json_file(data, folder="log", file_name="log.json"):
    """
    Save error documentation to a JSON file in the specified folder.
    
    Args:
        data (dict): Error documentation to save
        folder (str): Name of the folder to save the file in (default: "log")
        filename (str): Name of the output file (default: "log.json")
    """
    import json
    import os
    
    try:
        # Create the folder if it doesn't exist
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Created folder: {folder}")
        
        # Full path to the file
        filepath = os.path.join(folder, file_name)
        
        # Check if file exists and has content
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            # Read existing content
            with open(filepath, 'r') as f:
                try:
                    existing_data = json.load(f)
                    # Merge with new data
                    existing_data.update(data)
                    data = existing_data
                except json.JSONDecodeError:
                    print(f"Warning: {filepath} contains invalid JSON. Overwriting file.")
        
        # Write to file
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)
        ctx.log.error(f"Error documentation saved to {filepath}")
        
    except Exception as e:
        ctx.log.error(f"Error saving to {file_name}: {str(e)}")

