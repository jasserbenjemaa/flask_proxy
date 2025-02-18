from mitmproxy import ctx, http
import json

def request(flow: http.HTTPFlow) -> None:
    # Only intercept GET requests from frontend to backend
    if flow.request.method == "GET" and "/" in flow.request.pretty_url:
        try:
            # Check if there's content in the request
            if flow.request.content:
                content = json.loads(flow.request.content)
               # if "message" in content:
               #     # Log original message
               #     ctx.log.info(f"Original message: {content['message']}")
               #     # Change message to "jasser"
               #     content["message"] = "hello from proxy"
               #     # Update request content
               #     flow.request.content = json.dumps(content).encode()
               #     ctx.log.info(f"Modified message: {content['message']}")

            # Update request headers for forwarding
            flow.request.headers["Host"] = "backend:5100"
            flow.request.scheme = "http"
            flow.request.host = "backend"
            flow.request.port = 5100

        except Exception as e:
            ctx.log.error(f"Error modifying request: {e}")

def response(flow: http.HTTPFlow) -> None:
    try:
        if flow.response and flow.response.content:
            response_data = json.loads(flow.response.content)
            if "message" in response_data:
                response_data["message"] = "bace"
                flow.response.content = json.dumps(response_data).encode()
            ctx.log.info(f"Response from backend: {flow.response.content.decode('utf-8')}")
    except Exception as e:
        ctx.log.error(f"Error logging response: {e}")
