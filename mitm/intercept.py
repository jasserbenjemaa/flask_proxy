from mitmproxy import ctx, http  # type: ignore
import traceback
import json
import httpx  # type: ignore
from utils import fix_api, get_file_path

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
        ctx.log.error(f"Error in request interception: {error_trace}")


def response(flow: http.HTTPFlow) -> None:
    try:
        # Only process specific status codes
        if flow.response.status_code in [400, 422,500]:

            # Parse backend error and original client request
            backend_errors = flow.response.content.decode("utf-8")
            client_req = original_client_flow.request.content.decode("utf-8")
            file_path = get_file_path(original_client_flow)

            # Attempt to resolve the error with multiple tries
            for attempt in range(40):
                try:
                    # Request LLM assistance for error correction
                    with httpx.Client() as client:
                        llm_response = client.post(
                            "http://llm:5000/api",
                            json={
                                "client_req": client_req,
                                "backend_errors": backend_errors,
                                "file_path":file_path,
                                "content_type": original_client_flow.request.headers.get("Content-Type", "")

                            },
                            timeout=40.0
                        )

                    # Fix the client request
                    fixed_client_req = fix_api(client_req,file_path)

                    # Prepare headers with correct Content-Length
                    headers = dict(original_client_flow.request.headers)


                    headers['Content-Length'] = str(len(fixed_client_req.encode('utf-8')))

                    # Send the corrected request
                    with httpx.Client() as client:
                        response = client.request(
                            method=original_client_flow.request.method,
                            url=original_client_flow.request.url,
                            headers=headers,
                            cookies=original_client_flow.request.cookies,
                            content=fixed_client_req.encode('utf-8')
                        )

                    backend_errors=response.content.decode('utf-8')
                    ctx.log.info(f"{backend_errors}")

                    # Log the response status
                    ctx.log.info(f"Attempt {attempt + 1}/20 - Response status: {response.status_code}____________________________________________________")

                    # If successful, update the flow response and break
                    if response.status_code not in [400, 422,500]:
                        flow.response.content = response.content
                        break


                except Exception as attempt_error:
                    ctx.log.error(f"Attempt {attempt + 1} failed: {str(attempt_error)}")


    except Exception as e:
        error_trace = traceback.format_exc()
        ctx.log.error(f"Error in response handling: {error_trace}")