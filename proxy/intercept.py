from mitmproxy import ctx, http # type: ignore
import json
import httpx # type: ignore


def request(flow: http.HTTPFlow) -> None:
    # Only intercept POST requests from frontend to backend
        try:
            if flow.request.method == "POST":
                req_content = json.loads(flow.request.content)

                res_from_llm = httpx.post("http://llm:5000/api",json=req_content)
                res_from_llm.raise_for_status()
                #ctx.log.info(f"llm msg : {res_from_llm}")

                flow.request.content = json.dumps(res_from_llm.json()).encode('utf-8')

        except Exception as e:
            ctx.log.error(f"Error modifying request: {e}")
