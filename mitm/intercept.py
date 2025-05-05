from mitmproxy import ctx, http  # type: ignore
import traceback
import json
from utils import fix_api, get_file_path,read_json_file,generate_error_documentation,save_to_json_file
from compare_json import compare_json

def request(flow: http.HTTPFlow) -> None:
    try:
        global original_client_flow
        original_client_flow = flow.copy()

        if flow.request.content:
            # Parse and potentially fix the request content
            file_path = get_file_path(flow)
            fixed_req_content = fix_api(flow.request.content.decode('utf-8'), file_path)
            flow.request.content = fixed_req_content.encode("utf-8")
    except Exception as e:
        error_trace = traceback.format_exc()
        ctx.log.error(f"Error in request interception: {error_trace} {e}")


def response(flow: http.HTTPFlow) -> None:
    try:
        # Only process specific status codes
        if flow.response.status_code in [400,401,403,404,409,429,500,503]:

            # Parse backend error and original client request
            client_req = original_client_flow.request.content.decode("utf-8")
            client_req_dict = json.loads(client_req)
            file_path = get_file_path(original_client_flow)

            url_path = original_client_flow.request.path
            method = original_client_flow.request.method
            status_code=flow.response.status_code

            json_schemas=read_json_file('request_schemas.json')
            compare_json_data=compare_json(json_schemas[url_path],client_req_dict)
            ctx.log.info(f"server_url:{compare_json_data},method:{method}")
            log_error=generate_error_documentation(url_path,status_code,method,compare_json_data['differences'])
            save_to_json_file(log_error)
            ctx.log.info(f"{log_error}")
            #make_correction_script(compare_json,method,url_path)




    except Exception as e:
        error_trace = traceback.format_exc()
        ctx.log.error(f"Error in response handling: {error_trace} {e}")