from mitmproxy import ctx, http  # type: ignore
import os
import traceback
import httpx
import json
from utils import fix_api, get_file_path,read_json_file,generate_error_documentation,save_to_json_file,check_provider,find_route_pattern
from generate_fix_data_script import generate_fix_data_script
from compare_json import compare_json
from urllib.parse import urlparse

BACKEND_URL = os.environ.get('BACKEND_URL', 'http://backend:5100')
parsed = urlparse(BACKEND_URL)
provider_name = parsed.hostname  # "backend"
provider_port = parsed.port 

try:
    json_schemas=read_json_file('request_schemas.json')
    codes=read_json_file("flask_routes.json")
except Exception as e:
    print(f"json_schemas is not found {e}")

    
def request(flow: http.HTTPFlow) -> None:
    try:
        url_path = flow.request.path
        url_pattern = find_route_pattern(url_path, routes_data=codes)
        
        if check_provider(provider_name,provider_port):
            flow.request.url=BACKEND_URL+url_path
            if flow.request.content:
                
                # Parse and potentially fix the request content
                file_path = get_file_path(flow,json_schemas.get(url_pattern,""))
                fixed_req_content = fix_api(flow.request.content.decode('utf-8'), file_path)
                flow.request.content = fixed_req_content.encode("utf-8")
        else:
            # FIX: Handle bytes content properly
            client_req_content = ""
            if flow.request.content:
            # Parse and potentially fix the request content
                file_path = get_file_path(flow,json_schemas.get(url_pattern,""))
                fixed_req_content = fix_api(flow.request.content.decode('utf-8'), file_path)
                flow.request.content = fixed_req_content.encode("utf-8")
                try:
                    # Try to decode as UTF-8 string
                    client_req_content = flow.request.content.decode('utf-8')
                except UnicodeDecodeError:
                    # If it's binary data, encode as base64 or handle differently
                    import base64
                    client_req_content = base64.b64encode(flow.request.content).decode('utf-8')
                    # Or you could skip binary content
                    # client_req_content = "[BINARY_DATA]"
            
            llm_req = {
                "client_req": client_req_content,  # Now it's a string, not bytes
                "url": BACKEND_URL + url_path,
                "code": codes.get(url_pattern, {}).get("code", "")
            }
            
            flow.request.url = "http://llm:6000/"
            flow.request.method = "POST"  # Change to POST for JSON data
            flow.request.headers["Content-Type"] = "application/json"  # Set content type
            data = json.dumps(llm_req)  # This should work now
            flow.request.content = data.encode('utf-8')
            flow.request.headers["Content-Length"] = str(len(flow.request.content))  # Update content length
         
            
        #flow_info(flow,"REQUEST")
        global original_client_flow
        original_client_flow = flow.copy()
    except Exception as e:
        error_trace = traceback.format_exc()
        ctx.log.error(f"Error in request interception: {error_trace} {e}")


def response(flow: http.HTTPFlow) -> None:
    
    try:
        # Only process specific status codes
        if flow.response.status_code in [400,401,403,404,429,500,503] and flow.request.content :

            # Parse backend error and original client request
            client_req = original_client_flow.request.content.decode("utf-8")
            client_req_dict = json.loads(client_req)
            #file_path = get_file_path(compare_json_data['similarity'],original_client_flow)

            url_path = original_client_flow.request.path
            url_pattern = find_route_pattern(url_path, routes_data=codes)
            method = original_client_flow.request.method
            status_code=flow.response.status_code

            compare_json_data=compare_json(json_schemas.get(url_pattern,""),client_req_dict)
            ctx.log.info(f"compare_json_data:{compare_json_data},method:{method}")
            log_error=generate_error_documentation(url_pattern,status_code,method,compare_json_data['differences'])
            save_to_json_file(log_error)
            
            file_path = get_file_path(flow,json_schemas.get(url_pattern,""))
            generate_fix_data_script(compare_json_data['similarity'],file_path)
            fixed_req_content = fix_api(client_req, file_path)

            similarity=compare_json(json_schemas.get(url_pattern,""),json.loads(fixed_req_content))["similarity"]
            while compare_json(json_schemas.get(url_pattern,""),json.loads(fixed_req_content))["similarity"] != [] :
                generate_fix_data_script(compare_json_data['similarity']+similarity,file_path)
                #TODO:chof chnoi list mt3 similarity trier 3ala asses 9dach men '.' mawjoda lazem ykon men 0 l +inf bug lakano el 3aks wala m5alwdin
                fixed_req_content = fix_api(client_req, file_path)
                similarity+=compare_json(json_schemas.get(url_pattern,""),json.loads(fixed_req_content))["similarity"]


            headers = dict(original_client_flow.request.headers)
            headers['Content-Length'] = str(len(fixed_req_content.encode('utf-8')))
            with httpx.Client() as client:
                try:
                    response = client.request(
                        method=original_client_flow.request.method,
                        url=original_client_flow.request.url,
                        headers=headers,
                        cookies=original_client_flow.request.cookies,
                        content=fixed_req_content.encode('utf-8'),
                        timeout=httpx.Timeout(10.0)  # 10 seconds total timeout
                    )
                    flow.response.status_code=response.status_code
                    flow.response.content=response.content
                except httpx.TimeoutException as e:
                    ctx.log.error(f"Request timed out: {e}")
                
            
    except Exception as e:
        error_trace = traceback.format_exc()
        ctx.log.error(f"Error in response handling: {error_trace} {e}")
