from mitmproxy import ctx
import os
import subprocess
import traceback
import json
import hashlib


def get_file_path(server_url, method,client_req):
    str_key=""
    for key in sorted(client_req.keys()):
        str_key+=key
    file_name=f"{str(server_url).replace('http://','').replace('/','_')}_{method}_{str_key}"
    hash_file_name = hashlib.md5(file_name.encode()).hexdigest()
    return f"api_correction_scripts/{hash_file_name}.py"

def fix_api(api,file_path):
    try:
        ctx.log.info(f"Original request: {api}")

        if os.path.exists(file_path):
            fixed_api = subprocess.run(["python3", file_path, json.dumps(api)], capture_output=True)
            fixed_api = json.loads(fixed_api.stdout)
            ctx.log.info(f"Fixed request: {fixed_api}")
            return fixed_api
        else:
            ctx.log.info("script not found")
    except Exception as e:
        error_trace = traceback.format_exc()
        ctx.log.error(f"Error in fix_api: {error_trace}")
    return api
