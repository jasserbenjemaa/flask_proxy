from Graph.state import GraphState

def evaluator_router(state:GraphState)->str:
  if state['go_to']=="sql_exec" and state['sqls_result'][-1].get("valid") or state['go_to']=="func_exec" and state['funcs_result'][-1].get("valid"):
    return "planer"

  elif state['go_to']=="sql_exec" and not state['sqls_result'][-1].get("valid"):
    return "sql_exec"

  elif state['go_to']=="func_exec" and not state['funcs_result'][-1].get("valid"):
    return "func_exec"

  return "END"
