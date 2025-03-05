from mitmproxy import ctx, http  # type: ignore
import traceback
import json
import httpx  # type: ignore


def fix_api(api):
    try:
        import api_correction_scripts.client
        ctx.log.info(f"Original request: {api}")

        if hasattr(api_correction_scripts.client, "fix_api"):
            fixed_api = api_correction_scripts.client.fix_api(api)
            ctx.log.info(f"Fixed request: {fixed_api}")
            return fixed_api
        else:
            ctx.log.info("fix_api function doesn't exist in api_correction_scripts")
    except Exception as e:
        error_trace = traceback.format_exc()
        ctx.log.error(f"Error in fix_api: {error_trace}")
    return api

def request(flow: http.HTTPFlow) -> None:
    """
    Intercept and potentially modify the outgoing request.

    Args:
        flow (http.HTTPFlow): The HTTP flow to be processed
    """
    global original_client_flow
    original_client_flow = flow.copy()

    try:
        if flow.request.content:
            # Parse and potentially fix the request content
            req_content = json.loads(flow.request.content)

            fixed_req_content = fix_api(req_content)
            flow.request.content = json.dumps(fixed_req_content).encode("utf-8")
    except Exception as e:
        error_trace = traceback.format_exc()
        ctx.log.error(f"Error in request interception: {error_trace}")

def response(flow: http.HTTPFlow) -> None:
    """
    Intercept and handle backend responses, attempting to resolve errors.

    Args:
        flow (http.HTTPFlow): The HTTP flow to be processed
    """
    try:
        # Only process specific status codes
        if flow.response.status_code in [400, 422, 200]:
            ctx.log.info(f"Intercepted message: {flow.response.content.decode('utf-8')} || Status code: {flow.response.status_code}")

            # Parse backend error and original client request
            backend_error = json.loads(flow.response.content)
            client_req = json.loads(original_client_flow.request.content)

            # Attempt to resolve the error with multiple tries
            for attempt in range(3):

                try:
                    # Request LLM assistance for error correction
                    with httpx.Client() as client:
                        llm_response = client.post(
                            "http://llm:5000/api",
                            json={
                                "client_req": client_req,
                                "backend_error": backend_error
                            },
                            timeout=40.0
                        )

                    # Fix the client request
                    fixed_client_req = fix_api(client_req)

                    # Prepare headers with correct Content-Length
                    headers = dict(original_client_flow.request.headers)

                    # Create a fixed payload
                    fixed_payload = {
                        "name": "ajsser",
                        "id": 123,
                        "message": "msg",
                        "source": "src"
                    }
                    fixed_client_req_str = json.dumps(fixed_client_req)
                    headers['Content-Length'] = str(len(fixed_client_req_str.encode('utf-8')))

                    # Send the corrected request
                    with httpx.Client() as client:
                        response = client.request(
                            method=original_client_flow.request.method,
                            url=original_client_flow.request.url,
                            headers=headers,
                            cookies=original_client_flow.request.cookies,
                            content=fixed_client_req_str.encode('utf-8')
                        )
                    backend_error=response.text

                    ctx.log.info(f"backend error: {backend_error} || Status code: {response.status_code}")
                    # Log the response status
                    ctx.log.info(f"Attempt {attempt + 1}/3 - Response status: {response.status_code}____________________________________________________")

                    # If successful, update the flow response and break
                    if response.status_code not in [400, 422]:
                        flow.response.content = response.content
                        break



                except Exception as attempt_error:
                    ctx.log.error(f"Attempt {attempt + 1} failed: {str(attempt_error)}")

                    # If it's the last attempt, re-raise the error
                    if attempt == 2:
                        raise

    except Exception as e:
        error_trace = traceback.format_exc()
        ctx.log.error(f"Error in response handling: {error_trace}")