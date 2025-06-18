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
TABLE_NAME=os.environ.get('TABLE_NAME','users')
parsed = urlparse(BACKEND_URL)
provider_name = parsed.hostname  # "backend"
provider_port = parsed.port 

try:
    json_schemas=read_json_file('request_schemas.json')
    codes=read_json_file("flask_routes.json")
except Exception as e:
    print(f"json_schemas is not found {e}")


def get_schema_for_endpoint_method(url_pattern: str, method: str) -> dict:
    """
    Get the schema for a specific endpoint and HTTP method.
    
    Args:
        url_pattern: The URL pattern (e.g., "/users/<user_id>")
        method: The HTTP method (e.g., "POST", "PUT", "PATCH")
        
    Returns:
        Dictionary containing the schema for this endpoint-method combination
    """
    endpoint_schemas = json_schemas.get(url_pattern, {})
    if isinstance(endpoint_schemas, dict) and method in endpoint_schemas:
        return endpoint_schemas[method]
    return {}


def get_code_for_endpoint_method(url_pattern: str, method: str) -> str:
    """
    Get the code for a specific endpoint and HTTP method.
    
    Args:
        url_pattern: The URL pattern (e.g., "/users/<user_id>")
        method: The HTTP method (e.g., "GET", "POST", "PUT", "PATCH")
        
    Returns:
        String containing the code for this endpoint-method combination
    """
    endpoint_methods = codes.get(url_pattern, {})
    if isinstance(endpoint_methods, dict) and method in endpoint_methods:
        return endpoint_methods[method]
    return ""


def validate_and_fix_request(flow: http.HTTPFlow, url_pattern: str, method: str) -> bool:
    """
    Validate and fix PUT/PATCH request content against schema.
    Returns True if content was modified, False otherwise.
    """
    if method not in ['PUT', 'PATCH'] or not flow.request.content:
        return False
    
    try:
        # Parse the original request content
        client_req_content = flow.request.content.decode('utf-8')
        client_req_dict = json.loads(client_req_content)
        
        # Get the schema for this endpoint and method
        endpoint_schema = get_schema_for_endpoint_method(url_pattern, method)
        if not endpoint_schema:
            return False
        
        # Compare request against schema
        compare_json_data = compare_json(endpoint_schema, client_req_dict)
        ctx.log.info(f"PUT/PATCH validation - compare_json_data: {compare_json_data}, method: {method}")
        
        # If there are differences, try to fix them
        if not (compare_json_data['differences'] or compare_json_data['similarity']):
            return False
        
        # Log the validation issues
        log_error = generate_error_documentation(url_pattern, 0, method, compare_json_data['differences'])
        save_to_json_file(log_error)
        
        # Apply iterative fixes
        fixed_req_content = apply_iterative_fixes(client_req_content, endpoint_schema, compare_json_data, flow)
        
        # Update the flow with fixed content
        flow.request.content = fixed_req_content.encode("utf-8")
        flow.request.headers["Content-Length"] = str(len(flow.request.content))
        
        ctx.log.info(f"Fixed {method} request for {url_pattern}")
        return True
        
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        ctx.log.error(f"Error parsing {method} request content: {e}")
        return False
    except Exception as e:
        ctx.log.error(f"Error in {method} validation: {e}")
        return False


def apply_iterative_fixes(client_req_content: str, endpoint_schema: dict, compare_json_data: dict, flow: http.HTTPFlow) -> str:
    """Apply iterative fixes to request content until no more similarities exist."""
    file_path = get_file_path(flow, endpoint_schema)
    generate_fix_data_script(compare_json_data['similarity'], file_path)
    fixed_req_content = fix_api(client_req_content, file_path)
    
    # Iteratively fix until no more similarities
    similarity = compare_json(endpoint_schema, json.loads(fixed_req_content))["similarity"]
    while compare_json(endpoint_schema, json.loads(fixed_req_content))["similarity"] != []:
        generate_fix_data_script(compare_json_data['similarity'] + similarity, file_path)
        fixed_req_content = fix_api(client_req_content, file_path)
        similarity += compare_json(endpoint_schema, json.loads(fixed_req_content))["similarity"]
    
    return fixed_req_content


def handle_backend_routing(flow: http.HTTPFlow, url_path: str, url_pattern: str, method: str) -> None:
    """Handle direct backend routing."""
    flow.request.url = BACKEND_URL + url_path
    
    # Apply fixes for non-PUT/PATCH methods (PUT/PATCH already handled)
    if flow.request.content and method not in ['PUT', 'PATCH']:
        endpoint_schema = get_schema_for_endpoint_method(url_pattern, method)
        file_path = get_file_path(flow, endpoint_schema)
        fixed_req_content = fix_api(flow.request.content.decode('utf-8'), file_path)
        flow.request.content = fixed_req_content.encode("utf-8")


def handle_llm_routing(flow: http.HTTPFlow, url_path: str, url_pattern: str, method: str) -> None:
    """Handle LLM routing."""
    client_req_content = get_request_content_for_llm(flow, url_pattern, method)
    
    llm_req = {
        "client_req": client_req_content,
        "url": BACKEND_URL + url_path,
        "code": get_code_for_endpoint_method(url_pattern, method),
        "table_name": TABLE_NAME,
        "method": flow.request.method
    }
    
    flow.request.url = "http://llm:6000/process"
    flow.request.method = "POST"
    flow.request.headers["Content-Type"] = "application/json"
    data = json.dumps(llm_req)
    flow.request.content = data.encode('utf-8')
    flow.request.headers["Content-Length"] = str(len(flow.request.content))


def get_request_content_for_llm(flow: http.HTTPFlow, url_pattern: str, method: str) -> str:
    """Get and prepare request content for LLM processing."""
    if not flow.request.content:
        return ""
    
    # For PUT/PATCH, content is already fixed if needed
    if method not in ['PUT', 'PATCH']:
        endpoint_schema = get_schema_for_endpoint_method(url_pattern, method)
        file_path = get_file_path(flow, endpoint_schema)
        fixed_req_content = fix_api(flow.request.content.decode('utf-8'), file_path)
        flow.request.content = fixed_req_content.encode("utf-8")
    
    try:
        return flow.request.content.decode('utf-8')
    except UnicodeDecodeError:
        import base64
        return base64.b64encode(flow.request.content).decode('utf-8')


def request(flow: http.HTTPFlow) -> None:
    try:
        url_path = flow.request.path
        url_pattern = find_route_pattern(url_path, routes_data=codes)
        method = flow.request.method
        
        # Apply validation and fixing for PUT/PATCH methods
        validate_and_fix_request(flow, url_pattern, method)
        
        # Route the request
        if check_provider(provider_name, provider_port):
            handle_backend_routing(flow, url_path, url_pattern, method)
        else:
            handle_llm_routing(flow, url_path, url_pattern, method)
            
        # Store original flow for response function
        global original_client_flow
        original_client_flow = flow.copy()
        
    except Exception as e:
        error_trace = traceback.format_exc()
        ctx.log.error(f"Error in request interception: {error_trace} {e}")


def response(flow: http.HTTPFlow) -> None:
    try:
        # Only process specific status codes
        if flow.response.status_code in [400,401,403,404,429,500,503] and flow.request.content:

            # Parse backend error and original client request
            client_req = original_client_flow.request.content.decode("utf-8")
            client_req_dict = json.loads(client_req)

            url_path = original_client_flow.request.path
            url_pattern = find_route_pattern(url_path, routes_data=codes)
            method = original_client_flow.request.method
            status_code = flow.response.status_code

            # Get the schema for this specific endpoint and method
            endpoint_schema = get_schema_for_endpoint_method(url_pattern, method)
            
            compare_json_data = compare_json(endpoint_schema, client_req_dict)
            ctx.log.info(f"compare_json_data:{compare_json_data},method:{method}")
            log_error = generate_error_documentation(url_pattern, status_code, method, compare_json_data['differences'])
            save_to_json_file(log_error)
            
            file_path = get_file_path(flow, endpoint_schema)
            generate_fix_data_script(compare_json_data['similarity'], file_path)
            fixed_req_content = fix_api(client_req, file_path)

            similarity = compare_json(endpoint_schema, json.loads(fixed_req_content))["similarity"]
            while compare_json(endpoint_schema, json.loads(fixed_req_content))["similarity"] != []:
                generate_fix_data_script(compare_json_data['similarity'] + similarity, file_path)
                fixed_req_content = fix_api(client_req, file_path)
                similarity += compare_json(endpoint_schema, json.loads(fixed_req_content))["similarity"]

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
                    flow.response.status_code = response.status_code
                    flow.response.content = response.content
                except httpx.TimeoutException as e:
                    ctx.log.error(f"Request timed out: {e}")
                
    except Exception as e:
        error_trace = traceback.format_exc()
        ctx.log.error(f"Error in response handling: {error_trace} {e}")