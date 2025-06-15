import os
import json
from typing import Dict, Any,  Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from Graph.state import GraphState

load_dotenv()


class FlaskCodePlanner:
  """
  Intelligent planner that analyzes Flask code, predicts function outputs using LLM,
  then proceeds to SQL execution and formatting
  """

  def __init__(self, functions_json_path: Optional[str] = None):
    self.llm = ChatGoogleGenerativeAI(
      model="gemini-2.5-flash-preview-04-17",
      google_api_key=os.getenv("GEMINI_API_KEY"),
    )

    # Load function definitions
    self.function_definitions = {}
    if functions_json_path:
      self.load_function_definitions(functions_json_path)

    # Prompt for analyzing Flask code and determining functions to predict
    self.analysis_prompt = ChatPromptTemplate.from_messages([
      ("system", """You are a Flask code analyzer. Your job is to analyze Flask route code and identify all function calls that need to be predicted/simulated.

Available functions with their definitions:
{function_definitions}

Your task:
1. Identify all function calls in the Flask code
2. Only consider functions that are available in the function definitions
3. Determine the order of function execution based on dependencies
4. Extract parameters that would be passed to each function
5. Identify what data each function would need (from request, URL params, etc.)

Return a JSON response with:
{{
    "functions_to_predict": [
        {{
            "function_name": "function_name",
            "parameters": {{"param1": "value1", "param2": "value2"}},
            "depends_on": ["list_of_dependencies"],
            "context": "description of what this function does in the route"
        }}
    ],
    "execution_order": ["function1", "function2", "function3"],
    "has_database_operations": true/false
}}

IMPORTANT: Only include functions that exist in the available function definitions."""),
      ("human", """Analyze this Flask code:

Flask Code:
{flask_code}

Client Request Data:
{client_request}

URL Information:
{url}

Identify functions to predict and their execution order.""")
    ])

    # Prompt for predicting function outputs
    self.prediction_prompt = ChatPromptTemplate.from_messages([
      ("system", """You are a function execution predictor. Given a function definition and its expected parameters, predict what the function would return.

Function Definition:
{function_definition}

Your task:
1. Understand what the function does based on its code
2. Use the provided parameters to simulate execution
3. Consider the context of how it's being called in the Flask route
4. Return a realistic output that the function would produce

IMPORTANT RULES:
- Return only the predicted output/return value
- If function returns JSON, return valid JSON
- If function returns a string, return the string
- If function returns a number, return the number
- If function returns a complex object, return a realistic representation
- Consider error cases - if parameters are invalid, return appropriate error response
- Be realistic about what the function would actually do

Response format: Return ONLY the predicted function output, no explanations."""),
      ("human", """Predict the output for this function call:

Function Name: {function_name}
Parameters: {parameters}
Context: {context}
Additional Data Available: {additional_data}

What would this function return?""")
    ])

  def load_function_definitions(self, json_path: str):
    """Load function definitions from JSON file"""
    try:
      with open(json_path, 'r', encoding='utf-8') as f:
        self.function_definitions = json.load(f)
      print(f"✅ Loaded {len(self.function_definitions)} function definitions")
    except FileNotFoundError:
      print(f"❌ Functions JSON file not found: {json_path}")
      self.function_definitions = {}
    except json.JSONDecodeError as e:
      print(f"❌ Invalid JSON in functions file: {e}")
      self.function_definitions = {}

  def set_function_definitions(self, functions_dict: Dict[str, Any]):
    """Set function definitions directly from dictionary"""
    self.function_definitions = functions_dict

  def analyze_flask_code(self, flask_code: str, client_request: Dict[str, Any] = None, url: str = "") -> Dict[str, Any]:
    """Analyze Flask code to identify functions that need prediction"""
    try:
      # Prepare function definitions for prompt
      func_defs_str = json.dumps(self.function_definitions,
                                 indent=2) if self.function_definitions else "No functions available"

      messages = self.analysis_prompt.format_messages(
        flask_code=flask_code,
        function_definitions=func_defs_str,
        client_request=json.dumps(client_request or {}, indent=2),
        url=url
      )

      response = self.llm.invoke(messages)

      try:
        result = json.loads(response.content.strip())
        return result
      except json.JSONDecodeError:
        # Fallback analysis
        return self.fallback_analysis(flask_code)

    except Exception as e:
      print(f"❌ Flask code analysis failed: {e}")
      return self.fallback_analysis(flask_code)

  def fallback_analysis(self, flask_code: str) -> Dict[str, Any]:
    """Simple fallback analysis when LLM fails"""
    import re

    functions_found = []
    available_func_names = list(self.function_definitions.keys())

    # Find function calls in code
    for func_name in available_func_names:
      pattern = rf'{func_name}\s*\('
      if re.search(pattern, flask_code):
        functions_found.append({
          "function_name": func_name,
          "parameters": {},
          "depends_on": [],
          "context": f"Function {func_name} called in Flask route"
        })

    return {
      "functions_to_predict": functions_found,
      "execution_order": [f["function_name"] for f in functions_found],
      "has_database_operations": bool(
        re.search(r'supabase\.table\(|\.select\(|\.insert\(|\.update\(', flask_code, re.IGNORECASE))
    }

  def predict_function_output(self, function_name: str, parameters: Dict[str, Any] = None,
                              context: str = "", additional_data: Dict[str, Any] = None) -> Any:
    """Predict what a function would return using LLM"""
    try:
      if function_name not in self.function_definitions:
        return f"Error: Function {function_name} not found in definitions"

      function_def = self.function_definitions[function_name]

      messages = self.prediction_prompt.format_messages(
        function_name=function_name,
        function_definition=json.dumps(function_def, indent=2),
        parameters=json.dumps(parameters or {}, indent=2),
        context=context,
        additional_data=json.dumps(additional_data or {}, indent=2)
      )

      response = self.llm.invoke(messages)
      predicted_output = response.content.strip()

      # Try to parse as JSON if it looks like JSON
      if predicted_output.startswith('{') or predicted_output.startswith('['):
        try:
          return json.loads(predicted_output)
        except json.JSONDecodeError:
          pass

      # Try to parse as number
      try:
        if '.' in predicted_output:
          return float(predicted_output)
        else:
          return int(predicted_output)
      except ValueError:
        pass

      # Return as string
      return predicted_output

    except Exception as e:
      return f"Error predicting {function_name}: {str(e)}"

  def predict_all_functions(self, analysis_result: Dict[str, Any],
                            client_request: Dict[str, Any] = None, url: str = "") -> Dict[str, Any]:
    """Predict outputs for all identified functions"""
    predicted_results = {}
    additional_data = {
      "client_request": client_request or {},
      "url": url,
      "predicted_results": predicted_results  # Allow functions to depend on previous results
    }

    functions_to_predict = analysis_result.get("functions_to_predict", [])
    execution_order = analysis_result.get("execution_order", [])

    # Execute functions in order
    for func_name in execution_order:
      # Find function details
      func_details = next((f for f in functions_to_predict if f["function_name"] == func_name), None)
      if not func_details:
        continue

      print(f"🔮 Predicting output for: {func_name}")

      # Update additional data with previous results
      additional_data["predicted_results"] = predicted_results

      predicted_output = self.predict_function_output(
        function_name=func_name,
        parameters=func_details.get("parameters", {}),
        context=func_details.get("context", ""),
        additional_data=additional_data
      )

      predicted_results[func_name] = predicted_output
      print(f"✅ Predicted result for {func_name}: {predicted_output}")

    return predicted_results


def planner_node(state: GraphState) -> Dict[str, Any]:
  """
  Main planner node that predicts function outputs, then proceeds to SQL and formatting

  Args:
      state: Current GraphState containing code, function definitions, and other data

  Returns:
      Updated state with predicted function results and next action
  """
  try:
    # Extract information from state
    flask_code = state.get("code", "")
    functions_json_path = state.get("functions_json_path")
    client_request = state.get("client_req", {})
    url = state.get("url", "")

    if not flask_code.strip():
      return {
        "next_action": "error",
        "error": "No Flask code provided for planning"
      }

    # Initialize planner
    planner = FlaskCodePlanner()

    # Load function definitions
    if functions_json_path:
      planner.load_function_definitions(functions_json_path)

    if not planner.function_definitions:
      print("⚠️  No function definitions loaded, proceeding without function prediction")

    # Step 1: Analyze Flask code
    print("🔍 Analyzing Flask code...")
    analysis_result = planner.analyze_flask_code(flask_code, client_request, url)

    # Step 2: Predict function outputs
    print("🔮 Predicting function outputs...")
    predicted_functions = planner.predict_all_functions(analysis_result, client_request, url)

    # Step 3: Determine next action
    has_db_operations = analysis_result.get("has_database_operations", False)

    if has_db_operations:
      next_action = "run_sql"
    else:
      next_action = "finalize"


    print(f"✅ Planning complete. Next action: {next_action}")
    print(f"📊 Predicted {len(predicted_functions)} function outputs")

    return {
      "funcs_result": predicted_functions,
      "function_analysis": analysis_result,
      "next_action": next_action,
    }

  except Exception as e:
    print(f"❌ Planning failed: {e}")
    return {
      "next_action": "error",
      "error": f"Planning failed: {str(e)}"
    }


def should_continue_planning(state: GraphState) -> str:
  """
  Conditional edge function to determine the next step after planning

  Args:
      state: Current GraphState

  Returns:
      String indicating the next node to execute
  """
  next_action = state.get("next_step")

  if next_action == "run_sql":
    return "sql_exec"
  else:
    # Default to formatter
    return "formatter"

