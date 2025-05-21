from mitmproxy import ctx, http  # type: ignore
import traceback
import httpx
import json
from utils import fix_api, get_file_path,read_json_file,generate_error_documentation,save_to_json_file
from generate_fix_data_script import generate_fix_data_script
from compare_json import compare_json

try:
    json_schemas=read_json_file('request_schemas.json')
except Exception as e:
    print(f"json_schemas is not found {e}")
    
def request(flow: http.HTTPFlow) -> None:
    try:
        global original_client_flow
        original_client_flow = flow.copy()
        url_path = original_client_flow.request.path

        if flow.request.content:
            # Parse and potentially fix the request content
            file_path = get_file_path(flow,json_schemas[url_path])
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
            #file_path = get_file_path(compare_json_data['similarity'],original_client_flow)

            url_path = original_client_flow.request.path
            method = original_client_flow.request.method
            status_code=flow.response.status_code

            compare_json_data=compare_json(json_schemas[url_path],client_req_dict)
            ctx.log.info(f"compare_json_data:{compare_json_data},method:{method}")
            log_error=generate_error_documentation(url_path,status_code,method,compare_json_data['differences'])
            save_to_json_file(log_error)
            
            file_path = get_file_path(flow,json_schemas[url_path])
            generate_fix_data_script(compare_json_data['similarity'],file_path)
            fixed_req_content = fix_api(client_req, file_path)

            similarity=compare_json(json_schemas[url_path],json.loads(fixed_req_content))["similarity"]
            while compare_json(json_schemas[url_path],json.loads(fixed_req_content))["similarity"] != [] :
                generate_fix_data_script(compare_json_data['similarity']+similarity,file_path)
                #TODO:chof chnoi list mt3 similarity trier 3ala asses 9dach men '.' mawjoda lazem ykon men 0 l +inf bug lakano el 3aks wala m5alwdin
                fixed_req_content = fix_api(client_req, file_path)
                similarity+=compare_json(json_schemas[url_path],json.loads(fixed_req_content))["similarity"]


            headers = dict(original_client_flow.request.headers)
            headers['Content-Length'] = str(len(fixed_req_content.encode('utf-8')))
            with httpx.Client() as client:
                response = client.request(
                    method=original_client_flow.request.method,
                    url=original_client_flow.request.url,
                    headers=headers,
                    cookies=original_client_flow.request.cookies,
                    content=fixed_req_content.encode('utf-8')
                )
            flow.response.status_code=response.status_code
            flow.response.content=response.content
                
            
    except Exception as e:
        error_trace = traceback.format_exc()
        ctx.log.error(f"Error in response handling: {error_trace} {e}")
