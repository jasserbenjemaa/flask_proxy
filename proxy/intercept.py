from mitmproxy import ctx, http
import json
import gemini
def response(flow: http.HTTPFlow) -> None:
    with open("api_schema.json", "r") as file:
        api_schema = json.load(file)
    try:
        ctx.log.info(f"original msg: {flow.response.content.decode('utf-8')}")
        if flow.response and flow.response.content:
            response_data = json.loads(flow.response.content)
            response_data = gemini.correct_json(api_schema, response_data)
            flow.response.content = json.dumps(json.loads(response_data)).encode()
            ctx.log.info(f"new intercepted msg : {flow.response.content.decode('utf-8')}")
    except Exception as e:
        ctx.log.error(f"Error logging response: {e}")


def request(flow: http.HTTPFlow) -> None:
    # Only intercept GET requests from frontend to backend
    if flow.request.method == "GET" and "/" in flow.request.pretty_url:
        try:
            # Check if there's content in the request
            if flow.request.content:
                content = json.loads(flow.request.content)
            # Update request headers for forwarding
            flow.request.headers["Host"] = "backend:5100"
            flow.request.scheme = "http"
            flow.request.host = "backend"
            flow.request.port = 5100

        except Exception as e:
            ctx.log.error(f"Error modifying request: {e}")


