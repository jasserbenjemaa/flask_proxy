import os
from typing import Literal, Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from Graph.state import GraphState


class PlannerOutput(BaseModel):
  go_to: Literal["sql_exec", "func_exec"] = Field(
    ...,
    description="specify any node to go to sql_exec where execute sql or func_exec where execute function"
  )
  function_name: str = Field(description="specify the function name that you want its results")
  function_args: Dict[str, Any] = Field(description="specify the function arguments that will be passed to it")
  sql_snippet: str = Field(default="", description="extracted sql snippet from the flask code")
  the_final_result: Any = Field(description="the result of the code provided")
  is_there_err: str = Field(description="return the error if there is a problem in the code ")


def planer(state: GraphState) -> Dict[str, Any]:

  llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-preview-04-17",
    google_api_key=os.getenv("GEMINI_API_KEY"),
  )

  llm_structured_output = llm.with_structured_output(PlannerOutput)
  system_prompt = """
      Analyze the Flask code and client request to determine whether to route to SQL execution or function execution.

      ## Your Task
      1. Identify the route handling this request
      2. Determine if it uses SQL execution (any `execute()` methods, ORM queries) → extract the code snippet and route to `sql_exec` 
      so he can understand the code and return to the results
      3. If no SQL, identify function calls → route to `func_exec`
      4. Extract relevant function name and arguments
      5. If SQL is present, extract the SQL snippet
      6. Predict the expected result structure
  """

  user_prompt = """
      ### Flask Code
      ```python
      {flask_code}
      ```

      ### Client Request
      ```
      {client_request}
      ```

      This is the old calls results of:
      - Function executions: {function_exec}
      - SQL executions: {sql_exec}

      ## Example
      For SQL-based code like:
      ```python
      @app.route('/users/<int:user_id>')
      def get_user(user_id):
          cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
          user = cursor.fetchone()
          return jsonify({"id": user[0], "name": user[1]})
      ```

      With request `GET /users/123`, your response should be:
      ```json
      {
        "go_to": "sql_exec",
        "function_name": "get_user",
        "function_args": {"user_id": 123},
        "sql_snippet": "SELECT * FROM users WHERE id = %s",
        "the_final_result": {"id": 123, "name": "Example Name"},
        "is_there_err": "no"
      }
      ```

      For function-based code (no SQL):
      ```python
      @app.route('/calculate')
      def calculate():
          x = request.args.get('x', type=int)
          y = request.args.get('y', type=int)
          result = add_numbers(x, y)
          return jsonify({"result": result})
      ```

      With request `GET /calculate?x=5&y=10`, your response should be:
      ```json
      {
        "go_to": "func_exec",
        "function_name": "add_numbers",
        "function_args": {"x": 5, "y": 10},
        "sql_snippet": "",
        "the_final_result": {"result": 15},
        "is_there_err": "no"
      }
      ```
      Attention: this is in case if there is errors and you can proceed predict the best response that the backend can give and return it 
      don't return error .
      """

  prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", user_prompt)
  ])

  # Format and invoke the prompt
  formatted_prompt = prompt.format(
    flask_code=state.get('code', ''),
    client_request=state.get('client_req', ''),
    function_exec=state.get('funcs_result', []),
    sql_exec=state.get('sqls_result', [])
  )

  # Use the LLM with structured output
  result = llm_structured_output.invoke(formatted_prompt)

  # Update state based on route decision
  if result["go_to"] == "sql_exec":
    # Add new SQL result entry
    sql_results = state.get('sqls_result', [])
    sql_results.append({
      "result": None,  # Will be filled by sql_exec node
      "sql_code": result["sql_snippet"],
      "valid": False  # Will be updated by evaluator node
    })

    new_state = {
      "go_to": result["go_to"],
      "sqls_result": sql_results,
      "the_final_result": {"result": result['the_final_result']},
      "error": result["is_there_err"]
    }
  else:  # func_exec
    # Add new function result entry
    func_results = state.get('funcs_result', [])
    func_results.append({
      "result": None,  # Will be filled by func_exec node
      "func_code": result["function_name"],
      "args": result["function_args"],
      "valid": False  # Will be updated by evaluator node
    })

    new_state = {
      "go_to": result["go_to"],
      "funcs_result": func_results,
      "the_final_result": {"result": result['the_final_result']},
      "error": result["is_there_err"]
    }

  return new_state