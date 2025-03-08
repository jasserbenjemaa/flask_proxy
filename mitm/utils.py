from mitmproxy import ctx
import os
import subprocess
import traceback
import json
import hashlib
from urllib.parse import parse_qs
import cgi
from io import BytesIO

def convert_to_json(data, content_type):
    if content_type == "application/json":
        try:
            if isinstance(data, bytes):
                return json.loads(data.decode('utf-8'))
            return json.loads(data)
        except json.JSONDecodeError:
            ctx.log.error(f"Failed to parse JSON: {data}")
            return {"error": "Invalid JSON format"}
    elif content_type == "application/x-www-form-urlencoded":
        try:
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            return {key: value[0] for key, value in parse_qs(data).items()}
        except Exception as e:
            ctx.log.error(f"Failed to parse form data: {e}")
            return {"error": "Invalid form format"}
    elif content_type.startswith("multipart/form-data"):
        try:
            # Extract boundary from content-type
            boundary = content_type.split('boundary=')[1].strip()

            # Parse the multipart data
            environ = {'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': content_type}
            if isinstance(data, str):
                data = data.encode('utf-8')

            form = cgi.FieldStorage(
                fp=BytesIO(data),
                environ=environ,
                keep_blank_values=True
            )

            # Extract just the content from each field
            result = {}
            for field in form.keys():
                field_item = form[field]
                if hasattr(field_item, 'filename') and field_item.filename:
                    # File upload, get content
                    result[field] = field_item.file.read().decode('utf-8', errors='replace')
                else:
                    # Regular form field
                    result[field] = field_item.value

            return result
        except Exception as e:
            ctx.log.error(f"Failed to parse multipart data: {e}")
            return {"error": f"Failed to parse multipart: {str(e)}"}
    else:
        return {"error": f"Unsupported content type: {content_type}"}

def get_file_path(flow):
    server_url = flow.request.url
    method = flow.request.method
    content_type = flow.request.headers.get("Content-Type", "")

    try:
        client_req = convert_to_json(flow.request.content, content_type)
        str_key = ""
        for key in sorted(client_req.keys()):
            str_key += key

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
            ctx.log.info(f"Correction script not found")
    except subprocess.TimeoutExpired:
        ctx.log.error(f"Script execution timed out: {file_path}")
    except Exception as e:
        error_trace = traceback.format_exc()
        ctx.log.error(f"Error in fix_api: {error_trace}")

    return api