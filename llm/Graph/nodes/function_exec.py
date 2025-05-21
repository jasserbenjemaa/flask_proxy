import json
import os
from typing import Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from Graph.state import GraphState


def func_exec(state: GraphState) -> Dict[str, Any]:
  """
  Execute functions extracted from Flask code.
  This is a placeholder - actual implementation would depend on how you want to handle function execution.
  """
  llm = ChatGroq(model="deepseek-r1-distill-llama-70b")


  # Get the latest function entry from state
  latest_func_entry = state.get('funcs_result', [])[-1] if state.get('funcs_result', []) else None
  function_name = latest_func_entry.get('func_code', '') if latest_func_entry else ''
  function_args = latest_func_entry.get('args', {}) if latest_func_entry else {}

  # System prompt for function analysis
  system_prompt = """
    You are a specialized function analyzer for Flask applications. Your task is to:

    1. Analyze the Flask code and function details provided
    2. Determine what the function would return given the inputs
    3. Format the result as expected by the Flask application
    4. Check for potential errors in function execution

    Simulate the function execution and provide the expected result.
    """

  # User prompt template
  user_prompt = """
    ### Flask Code
    ```python
    {flask_code}
    ```

    ### Function to Execute
    Function name: {function_name}
    Function:{function}
    Arguments: {function_args}

    Please simulate the execution of this function with the given arguments and return what the result would be.
    Focus on determining the return value based on the logic in the Flask code.
    """

  # Create the prompt
  prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", user_prompt)
  ])

  # Format and invoke the prompt
  formatted_prompt = prompt.format(
    flask_code=state.get('code', ''),
    function_name=function_name,
    function=function_files.get(function_name,""),
    function_args=json.dumps(function_args)
  )

  # Simulate function execution using the LLM
  simulation_result = llm.invoke(formatted_prompt)

  # Parse the result (in a real implementation, you might have structured output here)
  function_result = {
    "status": "success",
    "data": str(simulation_result.content),
    "error": None
  }

  # Update the state with the execution results
  funcs_result = state.get('funcs_result', [])

  # Update the latest function result if it exists
  if funcs_result:
    funcs_result[-1]['result'] = function_result
    funcs_result[-1]['valid'] = True  # Assuming success for simulation

  # Prepare the new state
  new_state = {
    "funcs_result": funcs_result,
    "the_final_result": {
      "result": function_result["data"]
    },
    "error": None
  }

  return new_state