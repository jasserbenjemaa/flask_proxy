from typing import Dict, Any, List, Optional, TypedDict


class GraphState(TypedDict):
  """
    Represent the state of our Graph

    Attributes:
        code: flask code
        client_req: client request
        url: url of the endpoint
        supabase_res: the response returned by supabase
        go_to: go to the sql_exec or func_exec
        funcs_result: list contains all function results
        sqls_result: list contains all sql results
        feedback_on_work: feedback on the assistant's response
        the_final_result: the result of the code
        error: any error that occurred during processing
        function_files: dictionary containing function definitions (optional)

        # Planner-specific fields
        next_step: the next step determined by the planner
        execution_status: tracks what operations are needed and completed
        planner_analysis: stores the planner's analysis of the Flask code
        retry_count: tracks retry attempts for failed operations
        workflow_metadata: additional metadata for workflow tracking
    """

  code: str
  client_req: Dict[str, Any]
  url: str
  go_to: str
  funcs_result: List[Dict[str, Any]]  # [{result: Any, func_code: str, args: Dict, valid: bool}]
  sqls_result: List[Dict[str, Any]]  # [{result: Any, sql_code: str, executed_query: str, valid: bool}]
  the_final_result: Dict[str, Any]  # {"result": Any}
  error: Optional[str]

  functions_json_path:str

  # Planner-specific fields
  next_step: Optional[str]  # Next node to execute (SQL_EXEC, FUNC_EXEC, FORMATER)

