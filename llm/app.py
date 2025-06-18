from flask import Flask, request, jsonify
from typing import Dict, Any
import traceback
import os
from dotenv import load_dotenv

# Import your graph workflow
from Graph.graph import graph_init

load_dotenv()

app = Flask(__name__)

# Configure Flask
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
app.config['JSON_SORT_KEYS'] = False


class GraphWorkflowAPI:
  """Wrapper class for the graph workflow API"""

  def __init__(self):
    self.graph_app = None
    self._initialize_graph()

  def _initialize_graph(self):
    """Initialize the graph application"""
    try:
      self.graph_app = graph_init()
      print("✅ Graph workflow initialized successfully")
    except Exception as e:
      print(f"❌ Failed to initialize graph: {e}")
      self.graph_app = None

  def process_code(self, code: str,table_name:str="", client_req: Dict[str, Any] = None, url: str = "",method:str="GET") -> Dict[str, Any]:
    """
        Process Flask code through the graph workflow

        Args:
            code: Flask code to analyze and execute
            client_req: Client request data
            url: URL endpoint information
            table_name: the table of the db

        Returns:
            Dictionary containing the workflow result
        """
    if not self.graph_app:
      return {
        "success": False,
        "error": "Graph workflow not initialized",
        "result": None
      }

    # Prepare initial state
    initial_state = {
      "code": code,
      "client_req": client_req or {},
      "url": url,
      "table_name":table_name,
      "method":method,
      "functions_json_path": "sample_functions.json",
      "go_to": "",
      "funcs_result": [],
      "sqls_result": [],
      "the_final_result": {},
      "error": None,
      "next_step": None,
    }

    try:
      # Execute the workflow
      result = self.graph_app.invoke(initial_state)

      return {
        "success": True,
        "error": None,
        "result": result.get("the_final_result", {}),
        "execution_details": {
          "funcs_result": result.get("funcs_result", []),
          "sqls_result": result.get("sqls_result", []),
        }
      }

    except Exception as e:
      return {
        "success": False,
        "error": f"Workflow execution failed: {str(e)}",
        "result": None,
        "traceback": traceback.format_exc() if app.config['DEBUG'] else None
      }


# Initialize the workflow API
workflow_api = GraphWorkflowAPI()


@app.route('/process', methods=['POST'])
def process_flask_code():
  """
  Main endpoint to process Flask code through the graph workflow

  Expected JSON payload:
  {
      "code": "Flask route code to analyze and execute",
      "client_request": {"optional": "client data"},
      "url": "optional URL endpoint info"
  }
  """
  result = {}  # Initialize result as empty dict outside try block

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
    table_name=data.get('table_name',"")
    method=data.get('method',"")

    # Log the request (optional)
    if app.config['DEBUG']:
      print(f"📝 Processing code: {len(code)} characters")
      print(f"📋 Client request: {client_req}")
      print(f"🔗 URL: {url}")

    # Process through workflow
    result = workflow_api.process_code(code, client_req, url,table_name,method)


    return jsonify(result)

  except Exception as e:
    # Build error response, merging with any existing result data
    error_response = {
      "success": False,
      "error": f"Request processing failed: {str(e)}",
      **result  # Merge any existing result data
    }

    # Add workflow error if it exists in result
    if result.get("error"):
      error_response["workflow_error"] = result["error"]

    # Add debug information if in debug mode
    if app.config['DEBUG']:
      error_response["traceback"] = traceback.format_exc()

    return jsonify(error_response), 500



@app.route('/graph/visualize', methods=['GET'])
def visualize_graph():
  """Get the graph structure in Mermaid format"""
  try:
    if not workflow_api.graph_app:
      return jsonify({
        "success": False,
        "error": "Graph not initialized"
      }), 500

    mermaid_graph = workflow_api.graph_app.get_graph().draw_mermaid()
    print(mermaid_graph)

    return jsonify({
      "success": True,
      "mermaid": mermaid_graph,
      "format": "mermaid"
    })

  except Exception as e:
    return jsonify({
      "success": False,
      "error": f"Graph visualization failed: {str(e)}"
    }), 500



@app.errorhandler(404)
def not_found(error):
  """Handle 404 errors"""
  return jsonify({
    "success": False,
    "error": "Endpoint not found",
    "available_endpoints": [
      "GET /",
      "POST /process",
      "GET /graph/visualize",
    ]
  }), 404


@app.errorhandler(500)
def internal_error(error):
  """Handle 500 errors"""
  return jsonify({
    "success": False,
    "error": "Internal server error",
    "traceback": traceback.format_exc() if app.config['DEBUG'] else None
  }), 500


if __name__ == '__main__':
  # Development server
  print("🚀 Starting Flask API for Graph Workflow...")
  print(f"📊 Debug mode: {app.config['DEBUG']}")
  print("🔗 Available endpoints:")
  print("   - GET  / (health check)")
  print("   - POST /process (main processing)")
  print("   - POST /process/simple (simple processing)")
  print("   - GET  /graph/visualize (graph visualization)")
  print("   - POST /reinitialize (reinitialize graph)")

  app.run(
    host=os.getenv('FLASK_HOST', '0.0.0.0'),
    port=int(os.getenv('FLASK_PORT', 6000)),
    debug=app.config['DEBUG']
  )