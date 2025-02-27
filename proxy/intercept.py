from mitmproxy import ctx, http  # type: ignore
import json
import httpx  # type: ignore

req_content={}

def httpx_req_to_llm(res_backend,req_consumer):
    llm_config ={
            "provider":"gemini",
            "model":"gemini-2.0-flash-lite",
            "prompt":f"modify as you like this json {res_backend} {req_consumer}",#req_content
            "system_message":"",
            "temperature":1,
            "max_tokens":8000
            }
    try:
        res_from_llm = httpx.post("http://llm:5000/api", json=llm_config,timeout=20.0)
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
        if flow.request.method == "POST":
            req_content = json.loads(flow.request.content)  # Parse request JSON

            #res_from_llm=httpx_req_to_llm("jasser","jasser")
            # Replace the request content with the response from LLM
            #flow.request.content = json.dumps(res_from_llm.json()).encode("utf-8")

    except Exception as e:
        ctx.log.error(f"Error modifying request: {e}")


def response(flow: http.HTTPFlow) -> None:
    #intercepting the response from backend*
    try:
        if flow.response.status_code :
            ctx.log.info(f"new intercepted msg : {flow.response.content.decode('utf-8')} || status code:{flow.response.status_code}")

    except Exception as e:
        error_trace =   traceback.format_exc()
        ctx.log.error(f"Error logging response: {e}")

        #response_data["message"] = "Hello from proxy!"