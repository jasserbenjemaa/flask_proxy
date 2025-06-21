"""
Simple usage example showing how to use the general flask_response_formatter
"""
import json
from datetime import datetime
from dotenv import load_dotenv

# Import the modules
try:
  from Graph.nodes.formater import FlaskResponseFormatter, format_flask_response
except ImportError as e:
  print(f"❌ Import Error: {e}")
  print("Please ensure formater.py is in the correct path")
  exit(1)

load_dotenv()


def get_formatter_result(flask_code, client_request, url, table_name, method, use_llm=True, api_key=None):
  """
  Function to get formatter results and return as JSON
  
  Args:
      flask_code: The Flask application code
      client_request: The client request data
      url: The endpoint URL
      table_name: Database table name
      method: HTTP method
      use_llm: Whether to use LLM for pattern analysis (default: True)
      api_key: Google AI API key (optional)
  """

  try:
    # Use the convenient function
    result = format_flask_response(
      flask_code=flask_code,
      client_request=client_request,
      url=url,
      table_name=table_name,
      method=method,
      use_llm=use_llm,
      api_key=api_key
    )

    return result

  except Exception as e:
    error_result = {
      "success": False,
      "error": str(e),
      "formatted_response": {
        "data": {"error": "Service unavailable"},
        "status_code": 503
      },
      "timestamp": datetime.now().isoformat()
    }
    return error_result


def get_formatter_result_simple(flask_code, client_request, url, table_name, method, use_llm=True, api_key=None):
  """
  Simplified version that returns only the essential response data
  
  Returns:
      tuple: (success, response_data, status_code, error_message)
  """
  try:
    formatter = FlaskResponseFormatter(use_llm=use_llm, api_key=api_key)
    success, flask_response, error_msg = formatter.format_response_simple(
      flask_code, client_request, url, table_name, method
    )
    
    status_code = flask_response.get("status_code", 500)
    response_data = flask_response.get("data", {})
    
    return success, response_data, status_code, error_msg
    
  except Exception as e:
    return False, {"error": "Service unavailable"}, 503, str(e)