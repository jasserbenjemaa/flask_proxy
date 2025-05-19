from graph.state import GraphState

def sql_router( state: GraphState) -> str:
  last_message = state["messages"][-1]
  if hasattr(last_message, "tool_calls") and last_message.tool_calls:
    return "tools"  # Route to the ToolNode
  else:
    return "evaluator"
