import json
import time
import traceback
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
import logging
import re
import uuid
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv

# Import the sql_node function
try:
  from Graph.nodes.sql_node import sql_node
except ImportError as e:
  print(f"❌ Import Error: {e}")
  print("Please ensure sql_node.py is in the correct path")

load_dotenv()


class FlaskResponseFormatter:
  """
  General Flask response formatter that adapts to different Flask applications
  Uses minimal LLM calls only for pattern analysis when needed
  """

  def __init__(self, use_llm: bool = True, api_key: Optional[str] = None):
    """
    Initialize the Flask Response Formatter

    Args:
        use_llm: Whether to use LLM for pattern analysis (default: True)
        api_key: Google AI API key (optional, will use env var if not provided)
    """
    self.logger = logging.getLogger(__name__)
    self.use_llm = use_llm
    self.llm = None
    
    # Cache for response patterns to avoid repeated LLM calls
    self.pattern_cache = {}
    
    if use_llm:
      try:
        api_key = api_key or os.getenv('GEMINI_API_KEY')
        if api_key:
          self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            google_api_key=api_key,
            temperature=0.1,
            max_tokens=1024
          )
          self.logger.info("✅ LLM initialized for pattern analysis")
        else:
          self.logger.warning("⚠️ No API key provided, falling back to rule-based formatting")
          self.use_llm = False
      except Exception as e:
        self.logger.warning(f"⚠️ LLM initialization failed: {e}, falling back to rule-based formatting")
        self.use_llm = False
    
    self.logger.info(f"✅ Flask Response Formatter initialized (LLM: {'enabled' if self.use_llm else 'disabled'})")

  def _extract_general_info(self, url: str, method: str, client_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract general information about the request
    """
    # Extract path segments
    path_parts = [part for part in url.split('/') if part and not part.startswith('localhost') and ':' not in part]
    
    # Detect if this is an ID-based operation
    has_id = False
    resource_name = None
    operation_modifier = None
    
    if len(path_parts) >= 1:
      resource_name = path_parts[0]
    
    if len(path_parts) >= 2:
      # Check if second part looks like an ID (UUID, number, or generic ID)
      second_part = path_parts[1]
      if (re.match(r'^[0-9a-f-]{36}$', second_part) or  # UUID
          re.match(r'^\d+$', second_part) or            # Number
          len(second_part) > 8):                        # Likely an ID
        has_id = True
      else:
        operation_modifier = second_part
    
    if len(path_parts) >= 3 and has_id:
      operation_modifier = path_parts[2]
    
    # Determine operation type
    operation_type = self._determine_operation_type(method, has_id, operation_modifier, client_request)
    
    return {
      "resource_name": resource_name,
      "has_id": has_id,
      "operation_modifier": operation_modifier,
      "operation_type": operation_type,
      "path_parts": path_parts
    }

  def _determine_operation_type(self, method: str, has_id: bool, modifier: Optional[str], client_request: Dict[str, Any]) -> str:
    """
    Determine the operation type based on HTTP method and URL structure
    """
    if method == "POST":
      if modifier == "bulk":
        return "bulk_create"
      else:
        return "create"
    elif method == "GET":
      if modifier == "search":
        return "search"
      elif has_id:
        return "get_single"
      else:
        return "get_all"
    elif method == "PUT":
      return "update"
    elif method == "PATCH":
      return "patch"
    elif method == "DELETE":
      return "delete"
    else:
      return "unknown"

  def _analyze_flask_patterns(self, flask_code: str, cache_key: str) -> Dict[str, Any]:
    """
    Analyze Flask code to extract response patterns using minimal LLM calls
    """
    # Check cache first
    if cache_key in self.pattern_cache:
      return self.pattern_cache[cache_key]
    
    if not self.use_llm or not self.llm:
      # Fallback to rule-based pattern detection
      return self._extract_patterns_rule_based(flask_code)
    
    try:
      prompt = f"""
      Analyze this Flask code and extract the response patterns. Be concise and focus only on the response formats.

      ```python
      {flask_code}
      ```

      Return a JSON object with these patterns:
      {{
        "success_responses": {{
          "create": {{"returns": "object|array", "status_code": 201, "wrapper": null}},
          "get_all": {{"returns": "array", "status_code": 200, "wrapper": null}},
          "get_single": {{"returns": "object", "status_code": 200, "wrapper": null}},
          "update": {{"returns": "object", "status_code": 200, "wrapper": null}},
          "delete": {{"returns": "object", "status_code": 200, "wrapper": "message"}},
          "bulk_create": {{"returns": "object", "status_code": 201, "wrapper": "message"}}
        }},
        "error_responses": {{
          "not_found": {{"message": "User not found", "status_code": 404}},
          "duplicate": {{"message": "Email already exists", "status_code": 409}},
          "validation": {{"message": "Name and email are required", "status_code": 400}},
          "server_error": {{"message": "Internal server error", "status_code": 500}}
        }}
      }}

      Only return the JSON, no other text.
      """

      response = self.llm.invoke(prompt)
      response_text = response.content.strip()
      
      # Clean up response
      if '```json' in response_text:
        json_start = response_text.find('```json') + 7
        json_end = response_text.find('```', json_start)
        response_text = response_text[json_start:json_end].strip()
      elif '```' in response_text:
        json_start = response_text.find('```') + 3
        json_end = response_text.find('```', json_start)
        response_text = response_text[json_start:json_end].strip()
      
      patterns = json.loads(response_text)
      
      # Cache the result
      self.pattern_cache[cache_key] = patterns
      return patterns
      
    except Exception as e:
      self.logger.warning(f"LLM pattern analysis failed: {e}, using rule-based fallback")
      return self._extract_patterns_rule_based(flask_code)

  def _extract_patterns_rule_based(self, flask_code: str) -> Dict[str, Any]:
    """
    Extract response patterns using rule-based analysis
    """
    # Default patterns that work for most REST APIs
    return {
      "success_responses": {
        "create": {"returns": "object", "status_code": 201, "wrapper": None},
        "get_all": {"returns": "array", "status_code": 200, "wrapper": None},
        "get_single": {"returns": "object", "status_code": 200, "wrapper": None},
        "update": {"returns": "object", "status_code": 200, "wrapper": None},
        "patch": {"returns": "object", "status_code": 200, "wrapper": None},
        "delete": {"returns": "object", "status_code": 200, "wrapper": "message"},
        "bulk_create": {"returns": "object", "status_code": 201, "wrapper": "message"},
        "search": {"returns": "array", "status_code": 200, "wrapper": None}
      },
      "error_responses": {
        "not_found": {"message": "Resource not found", "status_code": 404},
        "duplicate": {"message": "Resource already exists", "status_code": 409},
        "validation": {"message": "Invalid request data", "status_code": 400},
        "no_data": {"message": "No data provided", "status_code": 400},
        "server_error": {"message": "Internal server error", "status_code": 500}
      }
    }

  def _format_success_response(self, data: Any, operation_type: str, patterns: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format successful response based on operation type and patterns
    """
    success_patterns = patterns.get("success_responses", {})
    pattern = success_patterns.get(operation_type, {"returns": "object", "status_code": 200, "wrapper": None})
    
    response_data = data
    status_code = pattern.get("status_code", 200)
    wrapper = pattern.get("wrapper")
    expected_returns = pattern.get("returns", "object")
    
    # Handle data formatting
    if isinstance(data, list):
      if expected_returns == "object" and len(data) > 0:
        response_data = data[0]  # Return first item for single object responses
      elif expected_returns == "array":
        response_data = data  # Return array as is
    elif data is None:
      if operation_type in ["get_single", "update", "patch"]:
        # These operations should return 404 if no data
        return {"data": {"error": "Resource not found"}, "status_code": 404}
      response_data = [] if expected_returns == "array" else {}
    
    # Apply wrapper if specified
    if wrapper == "message":
      if operation_type == "delete":
        response_data = {
          "message": "Resource deleted successfully",
          "deleted_resource": response_data
        }
      elif operation_type == "bulk_create":
        count = len(data) if isinstance(data, list) else 1
        response_data = {
          "message": f"{count} resources created successfully",
          "resources": data if isinstance(data, list) else [data]
        }
    
    return {"data": response_data, "status_code": status_code}

  def _format_error_response(self, errors: List[Dict], operation_type: str, patterns: Dict[str, Any], client_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format error response based on error details and patterns
    """
    error_patterns = patterns.get("error_responses", {})
    
    if not errors:
      pattern = error_patterns.get("server_error", {"message": "Unknown error occurred", "status_code": 500})
      return {"data": {"error": pattern["message"]}, "status_code": pattern["status_code"]}
    
    error = errors[0]
    error_message = error.get('error_message', 'Unknown error occurred')
    
    # Detect error type
    error_type = "server_error"  # default
    
    if any(keyword in error_message.lower() for keyword in ['duplicate', 'unique constraint', 'already exists']):
      error_type = "duplicate"
    elif any(keyword in error_message.lower() for keyword in ['not found', 'does not exist']):
      error_type = "not_found"
    elif any(keyword in error_message.lower() for keyword in ['required', 'missing', 'invalid']):
      error_type = "validation"
    elif not client_request and operation_type in ["create", "update", "patch"]:
      error_type = "no_data"
    
    pattern = error_patterns.get(error_type, error_patterns.get("server_error", {"message": error_message, "status_code": 500}))
    
    return {"data": {"error": pattern["message"]}, "status_code": pattern["status_code"]}

  def _validate_request_data(self, client_request: Dict[str, Any], operation_type: str, patterns: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    General request validation
    """
    error_patterns = patterns.get("error_responses", {})
    
    # Basic validation rules
    if operation_type in ["create", "update", "patch"] and not client_request:
      pattern = error_patterns.get("no_data", {"message": "No data provided", "status_code": 400})
      return {"data": {"error": pattern["message"]}, "status_code": pattern["status_code"]}
    
    if operation_type == "bulk_create":
      if not client_request.get('resources') and not any(key for key in client_request.keys() if isinstance(client_request[key], list)):
        pattern = error_patterns.get("validation", {"message": "Bulk data required", "status_code": 400})
        return {"data": {"error": pattern["message"]}, "status_code": pattern["status_code"]}
    
    return None

  def format_response(self,
                      flask_code: str,
                      client_request: Dict[str, Any],
                      url: str,
                      table_name: str,
                      method: str = "POST") -> Dict[str, Any]:
    """
    General pipeline: Execute SQL and format response to match Flask format

    Args:
        flask_code: Original Flask application code
        client_request: Client request data
        url: API endpoint URL
        table_name: Database table name
        method: HTTP method

    Returns:
        Formatted Flask-like response
    """

    start_time = time.time()

    self.logger.info(f"🚀 Starting general Flask response formatting for {method} {url}")
    print(f"🚀 Starting general Flask response formatting for {method} {url}")

    try:
      # Step 1: Extract general information about the request
      request_info = self._extract_general_info(url, method, client_request)
      operation_type = request_info["operation_type"]
      
      print(f"📝 Detected operation: {operation_type} on resource: {request_info.get('resource_name', 'unknown')}")

      # Step 2: Analyze Flask patterns (with caching)
      cache_key = f"{method}_{operation_type}_{hash(flask_code[:500])}"  # Use first 500 chars for cache key
      patterns = self._analyze_flask_patterns(flask_code, cache_key)
      
      print(f"🎯 Using patterns: {'LLM-analyzed' if cache_key not in self.pattern_cache else 'cached'}")

      # Step 3: Validate request data
      validation_error = self._validate_request_data(client_request, operation_type, patterns)
      if validation_error:
        print(f"❌ Validation failed: {validation_error}")
        return {
          "success": True,
          "formatted_response": validation_error,
          "sql_execution_result": None,
          "processing_time": time.time() - start_time,
          "timestamp": datetime.now().isoformat(),
          "metadata": {
            "method": method,
            "url": url,
            "table_name": table_name,
            "operation_type": operation_type,
            "validation_error": True,
            "patterns_source": "validation"
          }
        }

      # Step 4: Execute SQL using sql_node
      print("📝 Executing SQL with sql_node...")

      sql_client_request = {
        "method": method,
        "data": client_request,
        "params": {},
        "headers": {"Content-Type": "application/json"}
      }

      sql_result = sql_node(
        sample_flask_code=flask_code,
        client_request=sql_client_request,
        url=url,
        table_name=table_name
      )

      print(f"   ✅ SQL execution completed. Success: {sql_result.get('success', False)}")

      # Step 5: Format response based on SQL result and patterns
      print("🎨 Formatting response with detected patterns...")

      supabase_data = sql_result.get('supabase_data')
      success = sql_result.get('success', False)
      errors = sql_result.get('errors', [])

      if success and supabase_data is not None:
        formatted_response = self._format_success_response(supabase_data, operation_type, patterns)
      else:
        formatted_response = self._format_error_response(errors, operation_type, patterns, client_request)

      print(f"   ✅ Response formatted successfully")

      # Step 6: Create final result
      processing_time = time.time() - start_time

      result = {
        "success": True,
        "formatted_response": formatted_response,
        "sql_execution_result": sql_result,
        "processing_time": processing_time,
        "timestamp": datetime.now().isoformat(),
        "metadata": {
          "method": method,
          "url": url,
          "table_name": table_name,
          "operation_type": operation_type,
          "resource_name": request_info.get('resource_name'),
          "sql_success": sql_result.get('success', False),
          "data_count": len(sql_result.get('supabase_data', [])) if isinstance(sql_result.get('supabase_data'), list) else (1 if sql_result.get('supabase_data') else 0),
          "patterns_cached": cache_key in self.pattern_cache,
          "llm_used": self.use_llm
        }
      }

      print(f"🎉 Response formatting completed successfully in {processing_time:.2f}s")
      print(f"📊 Final Response: {json.dumps(formatted_response, indent=2, default=str)}")

      return result

    except Exception as e:
      processing_time = time.time() - start_time
      error_msg = str(e)

      self.logger.error(f"❌ Failed to format response: {error_msg}")
      print(f"❌ Failed to format response: {error_msg}")

      return {
        "success": False,
        "error": error_msg,
        "formatted_response": {
          "data": {"error": "Internal server error"},
          "status_code": 500
        },
        "processing_time": processing_time,
        "timestamp": datetime.now().isoformat(),
        "traceback": traceback.format_exc()
      }

  def format_response_simple(self,
                             flask_code: str,
                             client_request: Dict[str, Any],
                             url: str,
                             table_name: str,
                             method: str = "POST") -> tuple[bool, Dict[str, Any], str]:
    """
    Simple version that returns just the essential information

    Returns:
        tuple: (success, flask_response, error_message)
    """
    try:
      result = self.format_response(flask_code, client_request, url, table_name, method)

      if result["success"]:
        return True, result["formatted_response"], ""
      else:
        return False, result["formatted_response"], result.get("error", "Unknown error")

    except Exception as e:
      error_response = {
        "data": {"error": "Internal server error"},
        "status_code": 500
      }
      return False, error_response, str(e)


def format_flask_response(flask_code: str,
                          client_request: Dict[str, Any],
                          url: str,
                          table_name: str,
                          method: str = "POST",
                          use_llm: bool = True,
                          api_key: Optional[str] = None) -> Dict[str, Any]:
  """
  Convenient function to format Flask response in one call

  Args:
      flask_code: Original Flask application code
      client_request: Client request data
      url: API endpoint URL
      table_name: Database table name
      method: HTTP method
      use_llm: Whether to use LLM for pattern analysis
      api_key: Google AI API key

  Returns:
      Formatted response result
  """
  try:
    formatter = FlaskResponseFormatter(use_llm=use_llm, api_key=api_key)
    return formatter.format_response(flask_code, client_request, url, table_name, method)
  except Exception as e:
    return {
      "success": False,
      "error": str(e),
      "formatted_response": {
        "data": {"error": "Service unavailable"},
        "status_code": 503
      },
      "timestamp": datetime.now().isoformat()
    }


# Usage Example
if __name__ == "__main__":
  print("🧪 General Flask Response Formatter Example")
  print("=" * 60)

  # Test with different types of endpoints
  test_cases = [
    {
      "name": "User Creation",
      "client_request": {"name": "John", "email": "john@example.com"},
      "url": "localhost:5100/users",
      "method": "POST"
    },
    {
      "name": "Product Update",
      "client_request": {"title": "New Product", "price": 99.99},
      "url": "localhost:5100/products/abc123",
      "method": "PUT"
    },
    {
      "name": "Order Search",
      "client_request": {},
      "url": "localhost:5100/orders/search?status=pending",
      "method": "GET"
    },
    {
      "name": "Bulk User Creation",
      "client_request": {"users": [{"name": "User1", "email": "user1@test.com"}, {"name": "User2", "email": "user2@test.com"}]},
      "url": "localhost:5100/users/bulk",
      "method": "POST"
    }
  ]

  # Sample Flask code (simplified)
  sample_flask_code = """
  @app.route('/api/<resource>', methods=['POST'])
  @app.route('/api/<resource>/<id>', methods=['PUT', 'DELETE'])
  def handle_resource():
      # Generic handler
      return jsonify(result), 200
  """

  for i, test in enumerate(test_cases, 1):
    print(f"\n🔍 Test {i}: {test['name']}")
    print("-" * 40)
    
    try:
      # Test with LLM enabled
      result = format_flask_response(
        flask_code=sample_flask_code,
        client_request=test["client_request"],
        url=test["url"],
        table_name="generic_table",
        method=test["method"],
        use_llm=True
      )
      
      print(f"✅ Success: {result.get('success', False)}")
      print(f"🎯 Operation: {result.get('metadata', {}).get('operation_type', 'unknown')}")
      print(f"🧠 LLM Used: {result.get('metadata', {}).get('llm_used', False)}")
      
      formatted_response = result.get('formatted_response', {})
      print(f"📄 Response: {json.dumps(formatted_response, indent=2)}")
      
    except Exception as e:
      print(f"❌ Test failed: {e}")