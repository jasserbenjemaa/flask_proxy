from Graph.state import GraphState
def planer_router(state:GraphState)->str:
  if state['go_to']=="sql_exec":
    return "sql_exec"
  elif state['go_to']=='func_exec':
    return 'func_exec'
  return "END"
