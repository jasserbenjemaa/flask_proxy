from typing import Dict, Any
import os
import json
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from Graph.state import GraphState

load_dotenv()


def format_flask_response(state: GraphState) -> Dict[str, Any]:
  """
    Function to format Flask response using LLM based on provided code, results, and error (if any).

    Args:
        state (GraphState): Contains Flask code, SQL results, function results, and optional error info.

    Returns:
        Dict[str, Any]: Updated state with 'the_final_result' as a proper Python dict

    Raises:
        Exception: If LLM formatting fails
    """
  try:
    # Get state values with safe defaults
    flask_code = state.get("code", "")
    sql_results = state.get("sqls_result", "")
    function_results = state.get("funcs_result", "")
    error_message = state.get("error", "")
    client_request = state.get("client_req", {})
    url = state.get("url", "")


    # Initialize LLM
    llm = ChatGoogleGenerativeAI(
      model="gemini-2.5-flash-preview-04-17",
      google_api_key=os.getenv("GEMINI_API_KEY"),
    )

    # Prepare string values - escape any braces that might be in the content
    flask_code_str = str(flask_code).replace("{", "{{").replace("}", "}}") if flask_code else "None"
    sql_results_str = json.dumps(sql_results, indent=2, default=str).replace("{", "{{").replace("}",
                                                                                                "}}") if sql_results else "None"
    function_results_str = json.dumps(function_results, indent=2, default=str).replace("{", "{{").replace("}",
                                                                                                          "}}") if function_results else "None"
    error_message_str = str(error_message).replace("{", "{{").replace("}", "}}") if error_message else "None"
    client_request_str = str(client_request).replace("{", "{{").replace("}", "}}") if client_request else "None"


    # Updated system message to explicitly request structured output
    system_msg = """You are a Flask code formatter expert. Your job is to analyze Flask code and format the response exactly as the code should return it.

Given:
1. Flask route code
2. SQL execution results 
3. Function execution results
4. Optional error information

You must return a structured response in this EXACT format:
RESPONSE_DATA: <the actual response data as JSON>
STATUS_CODE: <HTTP status code as integer>

Rules:
- If `error` is present, treat it like an exception raised during execution
- For error responses, return appropriate status codes (e.g. 400, 500)
- For success responses, return 200 unless the Flask code specifies otherwise
- The RESPONSE_DATA should be valid JSON that represents what jsonify() would return
- Do not include markdown formatting, code blocks, or extra text
- Return only the structured format above

Example output format:
RESPONSE_DATA: {"message": "success", "data": [...]}
STATUS_CODE: 200

Or for errors:
RESPONSE_DATA: {"error": "Something went wrong"}
STATUS_CODE: 500"""

    human_msg = f"""Flask Code: {flask_code_str}

SQL Results: {sql_results_str}

Function Results: {function_results_str}

Error (if any): {error_message_str}

Client request: {client_request_str}

The url you can take some additional info if you need: {url}

Format and return exactly what this Flask code should return based on the provided results."""

    # Create messages manually to avoid ChatPromptTemplate formatting issues
    messages = [
      {"role": "system", "content": system_msg},
      {"role": "user", "content": human_msg}
    ]

    # Query the model
    response = llm.invoke(messages)
    raw_response = response.content.strip()


    # Parse the structured response
    response_data, status_code = parse_llm_response(raw_response)

    # Create the final result as a proper Python dictionary
    final_result = {
      "data": response_data,
      "status_code": status_code
    }


    # Return updated state
    new_state = {
      "the_final_result": final_result,
    }
    return new_state

  except Exception as e:
    print(f"DEBUG - Full exception: {repr(e)}")
    print(f"DEBUG - Exception type: {type(e)}")
    raise Exception(f"Formatting failed: {repr(e)}")


def parse_llm_response(raw_response: str) -> tuple[Dict[str, Any], int]:
  """
    Parse the LLM response to extract response data and status code.

    Args:
        raw_response: The raw response from the LLM

    Returns:
        tuple: (response_data_dict, status_code_int)
    """
  try:
    # Look for the structured format
    response_data_match = re.search(r'RESPONSE_DATA:\s*(.+)', raw_response)
    status_code_match = re.search(r'STATUS_CODE:\s*(\d+)', raw_response)

    if response_data_match and status_code_match:
      # Extract and parse response data
      response_data_str = response_data_match.group(1).strip()
      response_data = json.loads(response_data_str)

      # Extract status code
      status_code = int(status_code_match.group(1))

      return response_data, status_code
    else:
      # Fallback: try to parse as JSON if it looks like JSON
      if raw_response.strip().startswith('{') and raw_response.strip().endswith('}'):
        try:
          response_data = json.loads(raw_response.strip())
          # Default status code based on content
          status_code = 500 if "error" in response_data else 200
          return response_data, status_code
        except json.JSONDecodeError:
          pass

      # Fallback: try to extract JSON from markdown code blocks
      json_match = re.search(r'```json\s*\n(.*?)\n```', raw_response, re.DOTALL)
      status_match = re.search(r'```status\s*\n(\d+)\n```', raw_response)

      if json_match:
        response_data = json.loads(json_match.group(1))
        status_code = int(status_match.group(1)) if status_match else 200
        return response_data, status_code

      # Final fallback: return error response
      return {"error": "Failed to parse LLM response", "raw_response": raw_response}, 500

  except Exception as e:
    print(f"DEBUG - Parse error: {repr(e)}")
    return {"error": f"Parse error: {str(e)}", "raw_response": raw_response}, 500