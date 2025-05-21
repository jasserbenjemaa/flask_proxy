import os
from typing import Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from Graph.state import GraphState


def safe_get(state: GraphState, key: str, default: Any = None) -> Any:
  return state.get(key, default)

def evaluation(state:GraphState)->Dict[str,Any]:
  llm=ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-preview-04-17",
    google_api_key=os.getenv("GEMINI_API_KEY"),
  )
  execution_path = safe_get(state, 'go_to', '')
  flask_code = safe_get(state, 'code', '')
  client_request = safe_get(state, 'client_req', '')
  error = safe_get(state, 'error', None)

  sql_results = safe_get(state, 'sqls_result', [])
  func_results = safe_get(state, 'funcs_result', [])

  system_prompt = """You are a specialized evaluator for Flask application execution results..."""

  user_prompt = """
           ### Flask Code
           ```python
           {flask_code}
           ```
           ### Client Request
           ```
           {client_request}
           ```
           ### Execution Type
           {execution_type} Execution
           ### Execution Details
           ```json
           {execution_details}
           ```
           ### Final Result
           ```json
           {final_result}
           ```
           ### Error (if any)
           {error}
           Please evaluate...
           """
  prompt = ChatPromptTemplate.from_messages([
      ("system", system_prompt),
      ("human", user_prompt)
    ])

  formatted_prompt = prompt.format(
      flask_code=flask_code,
      client_request=client_request,
      error=str(error) if error else "None"
    )

  evaluation_res = llm.invoke(formatted_prompt)


  if execution_path=="sql_exec":
    sql_results[-1]['valid']=evaluation_res.isValic
    return {
        "sqls_result":sql_results
      }

  else:
    func_results[-1]['valid'] = evaluation_res.isValid
    return {
        "funcs_result": func_results
      }