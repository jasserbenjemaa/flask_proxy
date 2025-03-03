from mitmproxy import ctx, http  # type: ignore
import traceback
import json
import httpx  # type: ignore
import api_correction_scripts.client

def httpx_req_to_llm(client_req,backend_error):
    try:
        res_from_llm = httpx.post("http://llm:5000/api", json={"client_req":client_req,"backend_error":backend_error},timeout=40.0)
        res_from_llm.raise_for_status()
    except httpx.RequestError as exc:
        ctx.log.error(f"An error occurred while requesting {exc.request.url!r}: {exc}")
    except httpx.HTTPStatusError as exc:
        ctx.log.error(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}: {exc}")
    except httpx.TimeoutException as e:
        ctx.log.error("httpx -> request timed out")
    return res_from_llm


# MITM Interception
def request(flow: http.HTTPFlow) -> None:
    try:
        if flow.request.content:
            global req_content
            req_content= json.loads(flow.request.content)  # Parse request JSON
            ctx.log.info(f"original req {req_content}")
            try:
                if hasattr(api_correction_scripts.client,"fix_api"):
                    req_content= api_correction_scripts.client.fix_api(req_content)
                    ctx.log.info(f"fixed req {req_content}")
                else:
                    ctx.log.info("fix_api function does't exist in api_correction_sctipts")
            except Exception as e:
                error_trace = traceback.format_exc()
                ctx.log.error(f"Error logging response: {error_trace}")
            flow.request.content = json.dumps(req_content).encode("utf-8")



    except Exception as e:
        ctx.log.error(f"Error modifying request: {e}")


def response(flow: http.HTTPFlow) -> None:
    #intercepting the response from backend*
    try:
        if flow.response.status_code in [] :
            ctx.log.info(f"new intercepted msg : {flow.response.content.decode('utf-8')} || status code:{flow.response.status_code}")
            res_content=json.loads(flow.response.content)
            #correct_api_form_llm=httpx_req_to_llm(req_content,res_content)
            #flow.response.content = json.dumps(correct_api_from_llm.json()).encode("utf-8")

    except Exception as e:
        error_trace = traceback.format_exc()
        ctx.log.error(f"Error logging response: {error_trace}")

        #response_data["message"] = "Hello from proxy!"