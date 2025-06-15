from langgraph.constants import END
from langgraph.graph import StateGraph

from Graph.routers.planer_router import planer_router
from Graph.state import GraphState
from Graph.nodes.formater import format_flask_response
from Graph.nodes.planer import planner_node
from Graph.nodes.sql_exec import sql_exec
from Graph.const import SQL_EXEC,  PLANER,FORMATER



def graph_init():
  """
    Initialize the graph with proper flow control to prevent infinite loops.
    """
  graph_builder = StateGraph(GraphState)

  # Add nodes
  graph_builder.add_node(SQL_EXEC, sql_exec)
  graph_builder.add_node(FORMATER, format_flask_response)
  graph_builder.add_node(PLANER, planner_node)

  # Set entry point
  graph_builder.set_entry_point(PLANER)

  # Direct execution nodes to END after completing their work
  graph_builder.add_edge(PLANER,SQL_EXEC )
  graph_builder.add_edge(SQL_EXEC, FORMATER)
  graph_builder.add_edge(PLANER,FORMATER )
  graph_builder.add_edge(FORMATER, END)

  graph_builder.add_conditional_edges(PLANER,planer_router,{FORMATER:FORMATER,SQL_EXEC:SQL_EXEC})


  return graph_builder.compile()
