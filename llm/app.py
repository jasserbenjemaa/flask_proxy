from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from Graph.nodes.main import get_formatter_result

load_dotenv()

app = Flask(__name__)

# Configure Flask
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
app.config['JSON_SORT_KEYS'] = False


def format_error_message(error_str):
  """
  Extract a clean error message from the detailed error response
  """
  try:
    # Handle PostgreSQL/Supabase constraint errors
    if 'duplicate key value violates unique constraint' in error_str:
      if 'email' in error_str:
        return "Email already exists"
      elif 'username' in error_str:
        return "Username already exists"
      else:
        return "Duplicate value violates unique constraint"

    # Handle other common database errors
    if 'violates not-null constraint' in error_str:
      return "Required field is missing"

    if 'violates foreign key constraint' in error_str:
      return "Referenced record does not exist"

    if 'permission denied' in error_str:
      return "Insufficient permissions"

    if 'User not found' in error_str:
      return "User not found"

    if 'No data provided' in error_str:
      return "No data provided"

    # For other errors, try to extract a meaningful message
    # Remove technical details and return a clean message
    return "Operation failed"

  except Exception:
    return "An error occurred"


@app.route('/process', methods=['POST'])
def process_flask_code():
  """
  Main endpoint to process Flask code through the graph workflow

  Expected JSON payload:
  {
      "code": "Flask route code to analyze and execute",
      "client_request": {"optional": "client data"},
      "url": "optional URL endpoint info",
      "method": "optional method",
      "table_name": "optional table name"
  }
  """

  try:
    # Validate request
    if not request.is_json:
      return jsonify({
        "success": False,
        "error": "Request must be JSON"
      }), 400

    data = request.get_json()

    # Extract required fields
    code = data.get('code', '').strip()
    if not code:
      return jsonify({
        "success": False,
        "error": "Code field is required and cannot be empty"
      }), 400

    client_req = data.get('client_req', {})
    url = data.get('url', '')
    table_name = data.get('table_name', "")
    method = data.get('method', 'GET')

    # Process through workflow
    result = get_formatter_result(code, client_req, url, table_name, method)

    # Check if the operation was successful
    if result.get('success', False):
      # Return only the formatted response for successful operations
      formatted_response = result.get('formatted_response', {})

      # Return clean success response
      return jsonify({
        "success": True,
        "data": formatted_response.get('data', {}),
        "status_code": formatted_response.get('status_code', 200),
        "processing_time": result.get('processing_time', 0)
      }), formatted_response.get('status_code', 200)

    else:
      # Handle error cases
      error_message = result.get('error', 'Unknown error occurred')

      # Check if there's a formatted response with error details
      formatted_response = result.get('formatted_response', {})
      if formatted_response and 'data' in formatted_response:
        error_data = formatted_response.get('data', {})
        if isinstance(error_data, dict) and 'error' in error_data:
          error_message = error_data['error']

      # Clean up the error message
      clean_error = format_error_message(str(error_message))

      # Determine appropriate status code
      status_code = 500
      if formatted_response and 'status_code' in formatted_response:
        status_code = formatted_response['status_code']
      elif 'not found' in clean_error.lower():
        status_code = 404
      elif 'already exists' in clean_error.lower():
        status_code = 409
      elif 'required' in clean_error.lower() or 'missing' in clean_error.lower():
        status_code = 400

      return jsonify({
        "success": False,
        "error": clean_error,
        "status_code": status_code
      }), status_code

  except Exception as e:
    # Handle unexpected errors
    error_response = {
      "success": False,
      "error": "Internal server error",
      "status_code": 500
    }

    # In debug mode, include more details
    if app.config['DEBUG']:
      error_response["debug_error"] = str(e)

    return jsonify(error_response), 500


@app.route('/health', methods=['GET'])
def health_check():
  """Health check endpoint"""
  return jsonify({
    "status": "healthy",
    "service": "flask-formatter-api"
  }), 200


if __name__ == '__main__':
  app.run(
    host=os.getenv('FLASK_HOST', '0.0.0.0'),
    port=int(os.getenv('FLASK_PORT', 6000)),
    debug=app.config['DEBUG']
  )