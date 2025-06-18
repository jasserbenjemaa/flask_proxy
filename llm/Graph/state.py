from typing import Dict, Any, List, Optional, TypedDict


class GraphState(TypedDict):
  """
    Represent the state of our Graph

    Attributes:
        code: flask code
        client_req: client request
        url: url of the endpoint
        go_to: go to the sql_exec or func_exec
        table_name: the database name
        funcs_result: list contains all function results
        sqls_result: list contains all sql results
        the_final_result: the result of the code
        error: any error that occurred during processing

        # Planner-specific fields
        next_step: the next step determined by the planner
    """

  code: str
  client_req: Dict[str, Any]
  url: str
  go_to: str
  all_sql_results:str
  method:str
  table_name:str
  funcs_result: List[Dict[str, Any]]  # [{result: Any, func_code: str, args: Dict, valid: bool}]
  sqls_result: List[Dict[str, Any]]  # [{result: Any, sql_code: str, executed_query: str, valid: bool}]
  the_final_result: Dict[str, Any]  # {"result": Any}
  error: Optional[str]

  functions_json_path:str

  # Planner-specific fields
  next_step: Optional[str]  # Next node to execute (SQL_EXEC, FUNC_EXEC, FORMATER)

