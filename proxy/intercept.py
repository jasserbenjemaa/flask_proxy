from mitmproxy import ctx, http  # type: ignore
import json
import httpx  # type: ignore
from jsonschema import validate, exceptions

# Load the JSON schema from file
try:
    with open("data.json", "r") as file:
        json_schema = json.load(file)
except Exception as e:
    ctx.log.error(f"Error loading JSON schema: {e}")
    json_schema = None  # Prevents crashes if the file is missing

# Function to validate JSON against schema
def is_valid_json(data, schema):
    try:
        validate(instance=data, schema=schema)
        return True
    except exceptions.ValidationError as e:
        ctx.log.error(f"Invalid JSON: {e}")
        return False

# MITM Interception
def request(flow: http.HTTPFlow) -> None:
    try:
        if flow.request.method == "POST":
            req_content = json.loads(flow.request.content)  # Parse request JSON

            if json_schema and is_valid_json(req_content, json_schema):
                ctx.log.info("Valid JSON received. Letting request pass unchanged.")
            else:
                ctx.log.warning("Invalid JSON detected. Modifying request.")

                # Send invalid JSON to LLM for correction
                res_from_llm = httpx.post("http://llm:5000/api", json=req_content)
                res_from_llm.raise_for_status()

                # Replace the request content with the corrected response from LLM
                flow.request.content = json.dumps(res_from_llm.json()).encode("utf-8")

    except Exception as e:
        ctx.log.error(f"Error modifying request: {e}")
